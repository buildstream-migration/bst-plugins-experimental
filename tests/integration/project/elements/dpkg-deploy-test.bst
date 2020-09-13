kind: dpkg_deploy
description: dpkg-deploy test

build-depends:
- base.bst
- filename: dpkg-build-test.bst
  config:
    input: True
