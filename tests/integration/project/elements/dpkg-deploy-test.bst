kind: dpkg_deploy
description: dpkg-deploy test

depends:
- filename: base.bst
  type: build
- filename: dpkg-build-test.bst
  type: build

config:
  base: base.bst
  input: dpkg-build-test.bst
