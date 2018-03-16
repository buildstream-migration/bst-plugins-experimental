kind: dpkg_build
description: dpkg-build test

depends:
- filename: base.bst
  type: build

sources:
- kind: local
  path: src

config:
  build-commands:
    (<):
    - chmod +x debian/rules
