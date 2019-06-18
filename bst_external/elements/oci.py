# Copyright (c) 2019 Codethink Ltd.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors:
#        Valentin David <valentin.david@codethink.co.uk>

"""Builds a OCI or Docker image files

Configuration
=============

::

  mode: docker

Valid ``mode`` values are ``oci`` or ``docker``. ``oci`` will output
an OCI image according to the "Image Format Specification"[1]_ at the
time of this plugin was made. `docker` will output Docker images
according to "Docker Image Specification v1.2.0"[2]_.

.. [1] https://github.com/opencontainers/image-spec/blob/master/spec.md
.. [2] https://github.com/moby/moby/blob/master/image/spec/v1.2.md

::

  annotations:
    key1: value1

Optional. Only for OCI.

::

  images:
  - ...

Contains a series of images. Not to mix up with layers. Images do not
need to share layers. For example there may be an image for each
architecture.

The configuration of an image contains the following fields:

Image configuration
-------------------

::

  parent:
    element: other-image.bst
    image: 0

``parent`` is optional. If not provided, we are building an image with only
one layer. ``element`` is the build dependency of type ``oci`` which contains
the layers we want to import. ``image`` is the image index number. Default
value for ``image`` is 0.

::

  layer: mylayer.bst

``layer`` is a build dependency which provides the top
layer. Integration commands are not run. So you may want to use depend
on ``compose`` element to run those. `layer` is optional. If not
provided, parent layers will be just used and new configuration will
be set on an empty layer.

::

  architecture: amd64

Must be provided. Must be a "``GOARCH``" value.
https://github.com/golang/go/blob/master/src/go/build/syslist.go

::

  os: linux

Must be provided. Must be a "``GOOS``" value.
https://github.com/golang/go/blob/master/src/go/build/syslist.go

::

  variant: v8
  os.version: 1
  os.features: ['a', 'b']

OCI only. Optional. Only used in image index for selection of the
right image. ``os.version`` and ``os.features`` are Windows related.
``variant`` are for selection of processor variants. For example ARM
version.

::

  author: John Doe <john.doe@example.com>

Author of the layer/image. Optional.

::

  comment: Add my awesome app

Commit message for the layer/image. Optional.

::

  annotations: {'key1': 'value1'}

Optional. Only for OCI.

::

  tags: ['myapp:latest', 'myapp:1.0']

Tags for the images. Only for Docker.

::

  config:
    ...

Optional container config for the image.

Container configuration
-----------------------

All configurations here are optional.

Examples common for OCI and Docker:

::

  User: "webadmin"
  ExposedPorts: ["80/tcp", "8080"]
  Env: ["A=value", "B=value"]
  Entrypoint: ["/bin/myapp"]
  Cmd: ["--default-param"]
  Volumes: ["/var/lib/myapp"]
  WorkingDir: "/home/myuser"

OCI specific:

::

  Labels: {"a": "b"}
  StopSignals: "SIGKILL"

Docker specific:

::

  Memory: 2048
  MemorySwap: 4096
  CpuShares: 2
  Heathcheck:
    Test: ["CMD", "/bin/test", "param"]
    Interval: 50000000000
    Timeout: 10000000000
    Retries: 2

Usage
=====

The artifact generated is an un-tared image and need to be composed
into at tar file. This can be done with ``--tar`` of ``bst checkout``.

The image can be loaded by either ``podman load -i`` or ``docker load -i``.

For example:

::

  bst checkout element.bst --tar element.tar
  podman load -i element.tar

Notes
=====

The element will compute the layering on top of its parents. So the
layer should be provided complete with all the files of the result.

There is no creation dates added to the images to avoid problems with
reproducibility.

Each ``oci`` element can only add one layer. So if you need to build
multiple layers, you must provide an ``oci`` element for each. Remember
that only ``os`` and ``architecture`` are required, so you can make
relatively concise elements.

You can layer OCI on top of Docker images or Docker images on top of
OCI.  So no need to create both versions for images you use for
creating intermediate layers that do not need to be exported.

"""

import itertools
import stat
import os
import tempfile
import tarfile
import hashlib
import gzip
import json
import codecs
import shutil
import filecmp
from contextlib import contextmanager, ExitStack
from collections.abc import Mapping

from buildstream import Element, ElementError, Scope

class blob:
    def __init__(self, root, media_type=None, text=False, mode='oci', legacy_config=None):
        self.root = root
        self.descriptor = None
        self.media_type = media_type
        self.text = text
        self.mode = mode
        self.filename = None
        self.legacy_config = {}
        if legacy_config:
            self.legacy_config.update(legacy_config)
        self.legacy_id = None

    @contextmanager
    def create(self):
        with tempfile.NamedTemporaryFile(mode='w+b', dir=self.root, delete=False) as f:
            filename = f.name
            try:
                if self.text:
                    yield codecs.getwriter('utf-8')(f)
                else:
                    yield f
                self.descriptor = {}
                if self.media_type:
                    self.descriptor['mediaType'] = self.media_type
                f.seek(0, 2)
                self.descriptor['size'] = f.tell()
                f.seek(0)
                h = hashlib.sha256()
                while True:
                    data = f.read(16*1204)
                    if len(data) == 0:
                        break
                    h.update(data)
                if self.mode == 'oci':
                    self.descriptor['digest'] = 'sha256:{}'.format(h.hexdigest())
                    os.makedirs(os.path.join(self.root, 'blobs', 'sha256'), exist_ok=True)
                    self.filename = os.path.join(self.root, 'blobs', 'sha256', h.hexdigest())
                else:
                    assert self.mode == 'docker'
                    if self.media_type.endswith('+json'):
                        self.filename = os.path.join(self.root, '{}.json'.format(h.hexdigest()))
                        self.descriptor = '{}.json'.format(h.hexdigest())
                    elif self.media_type.startswith('application/vnd.oci.image.layer.v1.tar'):
                        blobdir = os.path.join(self.root, h.hexdigest())
                        os.makedirs(blobdir)
                        self.filename = os.path.join(blobdir, 'layer.tar')
                        with open(os.path.join(blobdir, 'VERSION'), 'w') as f:
                            f.write('1.0')
                        self.legacy_config['id'] = h.hexdigest()
                        self.legacy_id = h.hexdigest()
                        with open(os.path.join(blobdir, 'json'), 'w', encoding='utf-8') as f:
                            json.dump(self.legacy_config, f)
                        self.descriptor = os.path.join(h.hexdigest(), 'layer.tar')
                    else:
                        assert False
                os.rename(filename, self.filename)
            except:
                try:
                    os.unlink(filename)
                except:
                    pass
                raise

def safe_path(path):
    norm = os.path.normpath(path)
    if os.path.isabs(norm):
        return os.path.relpath(norm, '/')
    else:
        return norm

class OciElement(Element):
    def configure(self, node):
        self.node_validate(node, [
            'mode', 'gzip',
            'images', 'annotations'
        ])

        self.mode = self.node_get_member(node, str, 'mode', 'oci')
        if self.mode not in ['docker', 'oci']:
            raise ElementError('{}: Mode must be "oci" or "docker"'.format(self.node_provenance(node, 'mode')))

        self.gzip = self.node_get_member(node, bool, 'gzip', self.mode == 'oci')

        if 'annotations' not in node:
            self.annotations = None
        else:
            self.annotations = {}
            annotations = self.node_get_member(node, Mapping, 'images')
            for k, _ in self.node_items(annotations):
                v = self.node_subst_member(annotations, k)
                self.annotations[k] = v

        self.images = []
        for image in self.node_get_member(node, list, 'images'):
            self.node_validate(image, [
                'parent', 'layer',
                'architecture', 'variant',
                'os', 'os.version', 'os.features',
                'author', 'comment', 'config',
                'annotations'
            ] + (['tags'] if self.mode == 'docker' else []))
            parent = self.node_get_member(image, Mapping, 'parent', None)
            image_value = {}
            if parent:
                self.node_validate(parent, [
                    'element', 'image'
                ])

                parent = {
                    'element': self.node_get_member(parent, str, 'element'),
                    'image': self.node_get_member(parent, int, 'image', 0),
                    }

                image_value['parent'] = parent
            if 'layer' in image:
                image_value['layer'] = self.node_subst_list(image, 'layer')

            image_value['architecture'] = \
                self.node_subst_member(image, 'architecture')

            if 'tags' in image:
                image_value['tags'] = \
                    self.node_subst_list(image, 'tags')

            image_value['os'] = self.node_subst_member(image, 'os')

            if 'os.version' in image:
                image_value['os.version'] = \
                    self.node_subst_member(image, 'os.version')
            if 'os.features' in image:
                image_value['os.features'] = \
                    self.node_subst_list(image, 'os.features')
            if 'os.features' in image:
                image_value['variant'] = \
                    self.node_subst_member(image, 'variant')

            if 'author' in image:
                image_value['author'] = \
                    self.node_subst_member(image, 'author')

            if 'comment' in image:
                image_value['comment'] = \
                    self.node_subst_member(image, 'comment')

            if 'config' in image:
                config = self.node_get_member(image, Mapping, 'config')

                common_config = [
                    'User', 'ExposedPorts',
                    'Env', 'Entrypoint',
                    'Cmd', 'Volumes',
                    'WorkingDir'
                ]
                docker_config = [
                    'Memory', 'MemorySwap',
                    'CpuShares', 'Healthcheck',
                ]
                oci_config = [
                    'Labels', 'StopSignals'
                ]

                self.node_validate(config, common_config + (docker_config if self.mode == 'docker' else oci_config))

                config_value = {}
                for member in ['User', 'WorkingDir', 'StopSignal']:
                    if member in config:
                        config_value[member] = \
                            self.node_subst_member(config, member)

                for member in ['Memory', 'MemorySwap', 'CpuShares']:
                    if member in config:
                        config_value[member] = \
                            int(self.node_subst_member(config, member))

                for member in ['ExposedPort', 'Volumes',
                               'Env', 'EntryPoint', 'Cmd']:
                    if member in config:
                        config_value[member] = \
                            self.node_subst_list(config, member)

                if 'Labels' in config:
                    labels = self.node_get_member(config, Mapping, 'Labels')
                    config_value['Labels'] = {}
                    for k, v in self.node_items(config, labels):
                        config_value['Labels'][k] = v

                if 'Healthcheck' in config:
                    healthcheck = self.node_get_member(config, Mapping, 'Healthcheck')
                    self.node_validate(healthcheck, [
                        'Test', 'Interval',
                        'Timeout', 'Retries'
                    ])
                    config['Healthcheck'] = {}
                    if 'Test' in healthcheck:
                        config['Healthcheck']['Test'] = self.node_subst_list(healthcheck, 'Test')
                    for member in ['Interval', 'Timeout', 'Retries']:
                        if member in healthcheck:
                            config['Healthcheck'][member] = int(self.node_subst_member(healthcheck, member))

                image_value['config'] = config_value
            if 'annotations' in image:
                image_value['annotations'] = {}
                annotations = \
                    self.node_get_member(image, Mapping, 'annotations')
                for k, _ in self.node_items(config, annotations):
                    v = self.node_subst_member(annotations, k)
                    image_value['annotations'][k] = v

            self.images.append(image_value)

    def preflight(self):
        pass

    def get_unique_key(self):
        return {'annotations': self.annotations,
                'images': self.images}

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def _build_image(self, sandbox, image, root, output):
        parent = os.path.join(root, 'parent')
        parent_checkout = os.path.join(root, 'parent_checkout')

        if 'layer' in image:
            if os.path.exists(parent_checkout):
                shutil.rmtree(parent_checkout)
            os.makedirs(os.path.join(parent_checkout))

        layer_descs = []
        layer_files = []
        diff_ids = []
        history = None
        legacy_parent = None

        config = {}
        if 'author' in image:
            config['author'] = image['author']
        config['architecture'] = image['architecture']
        config['os'] = image['os']
        if 'config' in image:
            config['config'] = {}
            for k, v in image['config'].items():
                if k in ['ExposedPorts', 'Volumes']:
                    config['config'][k] = {}
                    for value in v:
                        config['config'][k][value] = {}
                else:
                    config['config'][k] = v

        if 'parent' in image:
            if os.path.exists(parent):
                shutil.rmtree(parent)
            dep = self.search(Scope.BUILD, image['parent']['element'])
            dep.stage_dependency_artifacts(sandbox, Scope.RUN,
                                           path='parent')
            if not os.path.exists(os.path.join(parent, 'index.json')):
                with open(os.path.join(parent, 'manifest.json'), 'r', encoding='utf-8') as f:
                    parent_index = json.load(f)
                parent_image = parent_index[image['parent']['image']]
                layers = parent_image['Layers']

                with open(os.path.join(parent, safe_path(parent_image['Config'])), 'r', encoding='utf-8') as f:
                    image_config = json.load(f)
                diff_ids = image_config['rootfs']['diff_ids']

                if 'history' in image_config:
                    history = image_config['history']

                for i, layer in enumerate(layers):
                    _, diff_id = diff_ids[i].split(':', 1)
                    with open(os.path.join(parent, safe_path(layer)), 'rb') as origblob:
                        if self.gzip:
                            targz_blob = blob(output, media_type='application/vnd.oci.image.layer.v1.tar+gzip', mode=self.mode)
                            with targz_blob.create() as gzipfile:
                                with gzip.GzipFile(filename=diff_id, fileobj=gzipfile,
                                                   mode='wb', mtime=1320937200) as gz:
                                    shutil.copyfileobj(origblob, gz)
                            layer_descs.append(targz_blob.descriptor)
                            layer_files.append(targz_blob.filename)
                            legacy_parent = tar_blob.legacy_id
                        else:
                            legacy_config = {
                                'os': image['os']
                            }
                            if legacy_parent:
                                legacy_config['parent'] = legacy_parent
                            tar_blob = blob(output, media_type='application/vnd.oci.image.layer.v1.tar', mode=self.mode)
                            with tar_blob.create() as newfile:
                                shutil.copyfileobj(origblob, newfile)
                            layer_descs.append(tar_blob.descriptor)
                            layer_files.append(tar_blob.filename)
                            legacy_parent = tar_blob.legacy_id
            else:
                with open(os.path.join(parent, 'index.json'), 'r', encoding='utf-8') as f:
                    parent_index = json.load(f)
                parent_image_desc = \
                    parent_index['manifests'][image['parent']['image']]
                algo, h = parent_image_desc['digest'].split(':', 1)
                with open(os.path.join(parent, 'blobs', safe_path(algo), safe_path(h)), 'r', encoding='utf-8') as f:
                    image_manifest = json.load(f)
                algo, h = image_manifest['config']['digest'].split(':', 1)
                with open(os.path.join(parent, 'blobs', safe_path(algo), safe_path(h)), 'r', encoding='utf-8') as f:
                    image_config = json.load(f)
                diff_ids = image_config['rootfs']['diff_ids']
                if 'history' in image_config:
                    history = image_config['history']
                for i, layer in enumerate(image_manifest['layers']):
                    _, diff_id = diff_ids[i].split(':', 1)
                    algo, h = layer['digest'].split(':', 1)
                    origfile = os.path.join(parent, 'blobs', safe_path(algo), safe_path(h))
                    with ExitStack() as e:
                        if 'layer' not in image and i+1 == len(image_manifest['layers']):
                            # The case were we do not add a layer, the last imported layer has to be fully reconfigured
                            legacy_config = {}
                            legacy_config.update(config)
                            if legacy_parent:
                                legacy_config['parent'] = legacy_parent
                        else:
                            legacy_config = {
                                'os': image['os']
                            }
                        if legacy_parent:
                            legacy_config['parent'] = legacy_parent
                        if self.gzip:
                            output_blob = blob(output, media_type='application/vnd.oci.image.layer.v1.tar+gzip', mode=self.mode)
                        else:
                            output_blob = blob(output, media_type='application/vnd.oci.image.layer.v1.tar', mode=self.mode, legacy_config=legacy_config)
                        outp = e.enter_context(output_blob.create())
                        inp = e.enter_context(open(origfile, 'rb'))
                        if layer['mediaType'].endswith('+gzip'):
                            if self.gzip:
                                shutil.copyfileobj(inp, outp)
                            else:
                                gz = e.enter_context(gzip.open(filename=inp, mode='rb'))
                                shutil.copyfileobj(gz, outp)
                        else:
                            if self.gzip:
                                gz = e.enter_context(gzip.GzipFile(filename=diff_id, fileobj=outp,
                                                                   mode='wb', mtime=1320937200))
                                shutil.copyfileobj(inp, gz)
                            else:
                                shutil.copyfileobj(inp, outp)

                    layer_descs.append(output_blob.descriptor)
                    layer_files.append(output_blob.filename)
                    legacy_parent = output_blob.legacy_id

        if 'parent' in image and 'layer' in image:
            for layer in layer_files:
                if self.gzip:
                    mode='r:gz'
                else:
                    mode='r:'
                with self.timed_activity('Decompressing layer {}'.format(layer)):
                    with tarfile.open(layer, mode=mode) as t:
                        members = []
                        for info in t.getmembers():
                            if '/../' in info.name:
                                continue
                            if info.name.startswith('../'):
                                continue

                            dirname, basename = os.path.split(info.name)
                            if basename == '.wh..wh..opq':
                                for entry in os.listdir(os.path.join(parent_checkout, dirname)):
                                    full_entry = os.path.join(parent_checkout, dirname, entry)
                                    if os.path.islink(full_entry) or not os.path.isdir(full_entry):
                                        os.unlink(full_entry)
                                    else:
                                        shutil.rmtree(full_entry)
                            elif basename.startswith('.wh.'):
                                full_entry = os.path.join(parent_checkout, dirname, basename[4:])
                                if os.path.islink(full_entry) or not os.path.isdir(full_entry):
                                    os.unlink(full_entry)
                                else:
                                    shutil.rmtree(full_entry)
                            else:
                                members.append(info)

                        t.extractall(path=parent_checkout, members=members)

        legacy_config = {}
        legacy_config.update(config)
        if legacy_parent:
            legacy_config['parent'] = legacy_parent

        if 'layer' in image:
            deps = []
            for name in image['layer']:
                dep = self.search(Scope.BUILD, name)
                dep.stage_dependency_artifacts(sandbox, Scope.RUN, path='layer')

            layer = os.path.join(root, 'layer')
            with self.timed_activity('Transforming into layer'):
                for root, dirs, files in os.walk(parent_checkout):
                    for f in itertools.chain(files, dirs):
                        rel = os.path.relpath(os.path.join(root, f), parent_checkout)
                        if not os.path.lexists(os.path.join(layer, rel)) \
                           and os.path.lexists(os.path.dirname(os.path.join(layer, rel))):
                            whfile = os.path.join(layer, os.path.relpath(root, parent_checkout), '.wh.' + f)
                            with open(whfile, 'w') as f:
                                pass

                if 'parent' in image:
                    for root, dirs, files in os.walk(layer):
                        for f in files:
                            new = os.path.join(root, f)
                            rel = os.path.relpath(os.path.join(root, f), layer)
                            old = os.path.join(parent_checkout, rel)
                            if os.path.lexists(old):
                                old_st = os.lstat(old)
                                new_st = os.lstat(new)
                                if old_st.st_mode != new_st.st_mode:
                                    continue
                                if int(old_st.st_mtime) != int(new_st.st_mtime):
                                    continue
                                if stat.S_ISLNK(old_st.st_mode):
                                    if os.readlink(old) == os.readlink(new):
                                        os.unlink(new)
                                else:
                                    if filecmp.cmp(new, old):
                                        os.unlink(new)

            with tempfile.TemporaryFile(mode='w+b') as tfile:
                with tarfile.open(fileobj=tfile, mode='w:') as t:
                    with self.timed_activity('Building layer tar'):
                        for root, dirs, files in os.walk(layer):
                            dirs.sort()
                            for f in itertools.chain(sorted(files), dirs):
                                path = os.path.join(root, f)
                                arcname = os.path.relpath(path, layer)
                                st = os.lstat(path)
                                tinfo = tarfile.TarInfo(name=arcname)
                                tinfo.uid = 0
                                tinfo.gid = 0
                                tinfo.mode = stat.S_IMODE(st.st_mode)
                                tinfo.mtime = st.st_mtime
                                if stat.S_ISDIR(st.st_mode):
                                    tinfo.type = tarfile.DIRTYPE
                                    t.addfile(tinfo, None)
                                elif stat.S_ISREG(st.st_mode):
                                    tinfo.type = tarfile.REGTYPE
                                    tinfo.size = st.st_size
                                    with open(path, 'rb') as fd:
                                        t.addfile(tinfo, fd)
                                elif stat.S_ISLNK(st.st_mode):
                                    tinfo.type = tarfile.SYMTYPE
                                    tinfo.linkname = os.readlink(path)
                                    t.addfile(tinfo, None)
                                else:
                                    raise ElementError('{}: Unexpected file type for: {}'.format(self, arcname))
                tfile.seek(0)
                tar_hash = hashlib.sha256()
                with self.timed_activity('Hashing layer'):
                    while True:
                        data = tfile.read(16*1024)
                        if len(data) == 0:
                            break
                        tar_hash.update(data)
                tfile.seek(0)
                if self.gzip:
                    targz_blob = blob(output, media_type='application/vnd.oci.image.layer.v1.tar+gzip', mode=self.mode)
                    with self.timed_activity('Compressing layer'):
                        with targz_blob.create() as gzipfile:
                            with gzip.GzipFile(filename=tar_hash.hexdigest(), fileobj=gzipfile,
                                               mode='wb', mtime=1320937200) as gz:
                                shutil.copyfileobj(tfile, gz)
                    layer_descs.append(targz_blob.descriptor)
                else:
                    copied_blob = blob(output, media_type='application/vnd.oci.image.layer.v1.tar', mode=self.mode, legacy_config=legacy_config)
                    with copied_blob.create() as copiedfile:
                        shutil.copyfileobj(tfile, copiedfile)
                    layer_descs.append(copied_blob.descriptor)
                    legacy_parent = copied_blob.legacy_id

            diff_ids.append('sha256:{}'.format(tar_hash.hexdigest()))

        if not history:
            history = []
        hist_entry = {}
        if 'layer' not in image:
            hist_entry['empty_layer'] = True
        if 'author' in image:
            hist_entry['author'] = image['author']
        if 'comment' in image:
            hist_entry['comment'] = image['comment']
        history.append(hist_entry)

        config['rootfs'] = {'type': 'layers',
                            'diff_ids': diff_ids}
        config['history'] = history
        config_blob = blob(output, media_type='application/vnd.oci.image.config.v1+json', text=True, mode=self.mode)
        with config_blob.create() as configfile:
            json.dump(config, configfile)

        if self.mode == 'docker':
            manifest = {
                'Config': config_blob.descriptor,
                'Layers': layer_descs
                }
            legacy_repositories = {}
            if 'tags' in image:
                manifest['RepoTags'] = image['tags']
                for tag in image['tags']:
                    name, version = tag.split(':', 1)
                    if name not in legacy_repositories:
                        legacy_repositories[name] = {}
                    legacy_repositories[name][version] = legacy_parent

            return manifest, legacy_repositories
        else:
            manifest = {
                'schemaVersion': 2
            }
            manifest['layers'] = layer_descs
            manifest['config'] = config_blob.descriptor
            if 'annotations' in image:
                manifest['annotations'] = image['annotations']
            manifest_blob = blob(output, media_type='application/vnd.oci.image.manifest.v1+json', text=True)
            with manifest_blob.create() as manifestfile:
                json.dump(manifest, manifestfile)
            platform = {
                'os': image['os'],
                'architecture': image['architecture']
            }
            if 'os.version' in image:
                platform['os.version'] = image['os.version']
            if 'os.features' in image:
                platform['os.features'] = image['os.features']
            if 'variant' in image:
                platform['variant'] = image['variant']
            manifest_blob.descriptor['platform'] = platform
            return manifest_blob.descriptor, {}

    def assemble(self, sandbox):
        root = sandbox.get_directory()
        output = os.path.join(root, 'output')
        os.makedirs(output)

        manifests = []
        legacy_repositories = {}

        image_counter = 1
        for image in self.images:
            with self.timed_activity('Creating image {}'.format(image_counter)):
                manifest, legacy_repositories_part = self._build_image(sandbox, image, root, output)
                manifests.append(manifest)
                legacy_repositories.update(legacy_repositories_part)

            image_counter += 1

        if self.mode == 'docker':
            with open(os.path.join(output, 'manifest.json'), 'w', encoding='utf-8') as f:
                json.dump(manifests, f)
            with open(os.path.join(output, 'repositories'), 'w', encoding='utf-8') as f:
                json.dump(legacy_repositories, f)
        else:
            index = {
                'schemaVersion': 2
            }
            index['manifests'] = manifests
            if self.annotations:
                index['annotations'] = self.annotations

            with open(os.path.join(output, 'index.json'), 'w', encoding='utf-8') as f:
                json.dump(index, f)

            oci_layout = {
                'imageLayoutVersion': '1.0.0'
            }
            with open(os.path.join(output, 'oci-layout'), 'w', encoding='utf-8') as f:
                json.dump(oci_layout, f)

        return 'output'

def setup():
    return OciElement
