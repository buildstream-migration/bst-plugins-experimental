.PHONY: all install clean
libs = lib1.so lib2.a lib3.so
hdrs = hdr1.h hdr2.h hdr3.h
all: $(libs)

$(libs): $(hdrs)
	touch $@

$(hdrs):
	touch $@

install: install-lib install-hdr

install-lib: $(libs)
	install -d ${DESTDIR}/${PREFIX}/testlibs2
	install -m 755 $? ${DESTDIR}/${PREFIX}/testlibs2

install-hdr: $(hdrs)
	install -d ${DESTDIR}/${PREFIX}/testincludes2
	install -m 755 $? ${DESTDIR}/${PREFIX}/testincludes2

clean:
	rm *.so *.a *.h
