kind: import
description: quilt test

depends:
- filename: base.bst
  type: build

sources:
- kind: local
  path: files
- kind: quilt
  path: patches
