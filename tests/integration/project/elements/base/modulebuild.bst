kind: modulebuild

depends:
- filename: base/alpine-image.bst
  type: build

config:
  configure-commands:
  - perl Build.PL --prefix "%{install-root}%{prefix}" --install_path lib="%{install-root}%{prefix}/local/lib/site_perl"

sources:
- kind: tar
  url: https://cpan.metacpan.org/authors/id/L/LE/LEONT/Module-Build-0.4229.tar.gz
  ref: 1fe491a6cda914b01bc8e592faa2b5404e9f35915ca15322f8f2a8d8f9008c18
