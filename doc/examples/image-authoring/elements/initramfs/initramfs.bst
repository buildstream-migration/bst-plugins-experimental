# elements/image/initramfs/initramfs.bst

kind: compose
description: Initramfs composition

depends:
  - filename: initramfs/busybox.bst
    type: build
  - filename: initramfs/initramfs-scripts.bst
    type: build

config:
  include:
  - runtime
