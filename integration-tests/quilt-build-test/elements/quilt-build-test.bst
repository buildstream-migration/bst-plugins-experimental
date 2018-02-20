kind: import
description: quilt test

depends:
- filename: dependencies/base-platform.bst
  type: build

sources:
- kind: local
  path: files
- kind: quilt
  path: patches
