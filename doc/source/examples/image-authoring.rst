.. _examples_image_authoring:

Building a system image
=======================

.. note::

   This example is distributed with BuildStream-external in the
   `doc/examples/image-authoring
   <https://gitlab.com/BuildStream/bst-external/tree/master/doc/examples/image-authoring>`_
   subdirectory.

Project structure
-----------------

We set a :ref:`project <projectconf>` definition as follows:

``project.conf``
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/project.conf
   :language: yaml

Since we require plugins currently not part of the core set, we set up
the plugins to be used by this project. In this case, we will use the
x86image plugin to create the image and the docker plugin to acquire a
base image to work with.

We also add :ref:`source aliases <project_source_aliases>` for a few
sources we will use.

``elements/base.bst``
~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/base.bst
   :language: yaml

This is the :mod:`import <elements.import>` element used to import the
base image that will write the image we want to create. This is a
`BuildStream docker image
<https://gitlab.com/BuildStream/buildstream-docker-images/tree/master/image-tools>`_
made to help using BuildStream to create OS images.

``elements/contents.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/contents.bst
   :language: yaml

This element defines the contents of our image. For this example, we
will set up an example containing `alpine Linux
<https://www.alpinelinux.org/>`_ and a hello world script. Since these
are best defined as two separate elements, we use a :mod:`stack
<elements.stack>` element to pull in these dependencies.

``elements/contents/alpine.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/contents/alpine.bst
   :language: yaml

This defines the aforementioned alpine Linux. It's a small Linux
distribution that's perfect for this sort of example.

.. note::

   Alpine Linux does *not* run the usual GNU coreutils, it's based on
   the fairly minimal BusyBox + musl instead. This distribution may
   not be suited for all projects.

``elements/contents/hello.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/contents/hello.bst
   :language: yaml

This contains the following script for testing purposes. This element
is really just there to show that we're not cheating and downloading
an alpine Linux image ;)

``files/hello/hello``

.. literalinclude:: ../../examples/image-authoring/files/hello/hello
   :language: sh

``elements/initramfs-gz.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/initramfs-gz.bst
   :language: yaml

This element will create our `initramfs
<https://en.wikipedia.org/wiki/Initial_ramdisk>`_. The initramfs will
be responsible for loading the correct modules to boot our system and
setting up anything else our kernel requires to run - in this case, to
showcase this, we will be loading disk drivers.

``elements/initramfs/busybox.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/initramfs/busybox.bst
   :language: yaml

This defines BusyBox - for the uninitiated, BusyBox is a set of basic
UNIX commands required to have a functioning Linux system (coreutils
in GNU land). It's often used for initramfs because it's small and
contains everything needed to bootstrap the system. For more info,
check `BusyBox's about page <https://www.busybox.net/about.html>`_.

``elements/initramfs/musl.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/initramfs/musl.bst
   :language: yaml

This defines `musl libc <https://www.musl-libc.org/>`_, a small C
library. It is required to run BusyBox.


``elements/image/initramfs/initramfs-scripts.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/initramfs/initramfs-scripts.bst
   :language: yaml

The init scripts to be run in the initramfs. They are what performs
the actual work of preparing the system:

``files/initramfs-scripts/init``

.. literalinclude:: ../../examples/image-authoring/files/initramfs-scripts/init
   :language: sh

``files/initramfs-scripts/shutdown``

.. literalinclude:: ../../examples/image-authoring/files/initramfs-scripts/shutdown
   :language: sh

``elements/initramfs/initramfs.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/initramfs/initramfs.bst
   :language: yaml

The initial file system loaded into the image. It contains the
musl+BusyBox initramfs and initramfs scripts.

``elements/image/linux.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/linux.bst
   :language: yaml

This element contains, well, Linux. If we're going to build an OS
image, it might as well be Linux. This will be the kernel deployed to
our OS image.

``elements/system.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/system.bst
   :language: yaml

This element stacks together all the image contents and ensures we
have only runtime files left. This is what is actually staged onto the
image.

``elements/image-x86_64.bst``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/image-authoring/elements/image-x86_64.bst
   :language: yaml

This is our :ref:`x86image` element. It will do perform the actual
image creation for us, using the image tools from
``elements/base.bst`` and writing contents from ``image/system.bst``.

Both dependencies are marked as ``build`` dependencies, since they
will not be part of our output. This may be slightly counter-intuitive
since ``image/system.bst`` is to represent our image contents, but the
literal files in it will not be a part of the artifact produced by
BuildStream.

In the ``variables`` section we set up the layout of the image. We set
up the partitioning scheme with ``boot-size``, ``root-size`` and
``swap-size``, we set our desired ``sector-size`` and we set how our
kernel will be invoked with ``kernel-args`` and ``kernel-name``.

+-----------+------------------------------+
|boot-size  |The size of the boot partition|
+-----------+------------------------------+
|rootfs-size|The size of the rootfs        |
+-----------+------------------------------+
|sector-size|The sector size               |
+-----------+------------------------------+
|swap-size  |The size of the swap partition|
+-----------+------------------------------+
|kernel-args|The kernel args to pass on    |
|           |boot                          |
+-----------+------------------------------+
|kernel-name|What to name the kernel binary|
+-----------+------------------------------+

The image also defines a little script to help run this project with
qemu in ``final-commands``. This is not necessary, and can be removed
from the element if not desired.

Building the image
------------------
We now have a project that defines a fully bootable system. We should
build it!

To do so, invoke `bst build
<https://buildstream.gitlab.io/buildstream/using_commands.html#invoking-build>`_
as such:

.. raw:: html
   :file: ../sessions/image-authoring.html
