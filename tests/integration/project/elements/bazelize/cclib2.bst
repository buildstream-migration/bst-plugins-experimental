kind: manual

build-depends:
- base.bst

sources:
- kind: local
  path: files/bazelize_src/shared
- kind: local
  path: files/bazelize_src/cclib2

config:
  build-commands:
  - make PREFIX="%{prefix}"
  install-commands:
  - make -j1 PREFIX="%{prefix}" DESTDIR="%{install-root}" install
