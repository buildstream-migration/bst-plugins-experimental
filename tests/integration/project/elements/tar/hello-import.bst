kind: import

public:
  bst:
    split-rules:
      hello:
      - /hello.c
      patch:
      - /test
      - /series

sources:
- kind: local
  path: files/src/hello.c
- kind: local
  path: files/patches/test
- kind: local
  path: files/patches/series
- kind: local
  path: src/Makefile
