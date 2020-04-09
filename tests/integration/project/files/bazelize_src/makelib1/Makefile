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
	install -d ${DESTDIR}/${PREFIX}/testlibs1
	install -m 755 $? ${DESTDIR}/${PREFIX}/testlibs1

install-hdr: $(hdrs)
	install -d ${DESTDIR}/${PREFIX}/testincludes1
	install -m 755 $? ${DESTDIR}/${PREFIX}/testincludes1

clean:
	rm *.so *.a *.h
