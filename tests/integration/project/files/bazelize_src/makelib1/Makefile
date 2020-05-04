.PHONY: all install
libs = lib1.so lib2.a lib3.so.1234.4321 lib4.pic.a lib5.a lib6.pic.lo lib7.lo
hdrs = hdr1.h hdr2.hh hdr3.hpp hdr4.hxx hdr5.inc hdr6.inl hdr7.H
all: $(libs)

$(libs): $(hdrs)
	touch $@

$(hdrs):
	touch $@

install: install-lib install-hdr

install-lib: $(libs)
	install -d ${DESTDIR}/${PREFIX}/testlibs1
	install -m 755 $? ${DESTDIR}/${PREFIX}/testlibs1

install-hdr: $(hdrs)
	install -d ${DESTDIR}/${PREFIX}/testincludes1
	install -m 755 $? ${DESTDIR}/${PREFIX}/testincludes1
