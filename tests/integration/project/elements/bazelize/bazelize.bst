kind: bazelize
build-depends:
- filename: bazelize/cclib1.bst
runtime-depends:
- filename: bazelize/cclib2.bst
sources:
- kind: local
  path: files/bazelize_src/app
config:
  bazel-rule: "cc_binary"
  linkopts:
  - "-lboost_system"
  - "-lboost_thread"
  copts:
  - "-I/include/someinc"
  - "-I/lib/inc"
