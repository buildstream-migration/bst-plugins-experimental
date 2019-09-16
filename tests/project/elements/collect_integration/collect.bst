kind: collect_integration
depends:
- filename: collect_integration/dep1.bst
  type: build
- filename: collect_integration/dep2.bst
  type: build
- filename: collect_integration/ignore.bst
  type: build

config:
  script-path: script.sh
  ignore:
  - collect_integration/ignore.bst
