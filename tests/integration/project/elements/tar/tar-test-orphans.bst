kind: tar_element

depends:
- filename: tar/hello-import.bst
  type: build

config:
  filename: hello
  exclude:
  - patch 
  include-orphans: False
