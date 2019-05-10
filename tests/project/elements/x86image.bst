kind: x86image

depends:
- filename: vm/minimal-vm.bst
  junction: base/freedesktop-junction.bst
  type: build
- filename: vm/deploy-tools.bst
  junction: base/freedesktop-junction.bst
  type: build

variables:
  boot-size: 38912K

  rootfs-size: 100M
  sector-size: 512
  swap-size: 40K

  kernel-args: root=/dev/sda2 rootfstype=ext4 init=/bin/sh console=ttyS0

config:
  base: vm/deploy-tools.bst
  input: vm/minimal-vm.bst
