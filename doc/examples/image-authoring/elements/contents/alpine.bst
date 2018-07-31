# elements/alpine.bst

kind: manual
description: The system to boot

sources:
  - kind: tar
    url: alpine:v3.8/releases/x86_64/alpine-minirootfs-3.8.0-x86_64.tar.gz
    ref: ae36d6ea2033131cfc649afa13d7271367c386e7a0dbd5b3d0671a2ede22a2f1

depends:
  - filename: base.bst
    type: build

config:
  build-commands:
    - rm -r dev/*
    - cp -r ./* %{install-root}
  strip-commands: []
