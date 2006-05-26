import os
import re

import cross
import download
import framework
import gub
import misc
import targetpackage

class Binutils (cross.Binutils):
    def configure_command (self):
        # Add --program-prefix, otherwise we get
        # i686-freebsd-FOO iso i686-freebsd4-FOO.
        return (cross.Binutils.configure_command (self)
            + misc.join_lines ('''
--program-prefix=%(tool_prefix)s
'''))

class Gcc (cross.Gcc):
    def configure_command (self):
        # Add --program-prefix, otherwise we get
        # i686-freebsd-FOO iso i686-freebsd4-FOO.
        return (cross.Gcc.configure_command (self)
            + misc.join_lines ('''
--program-prefix=%(tool_prefix)s
'''))

class Freebsd_runtime (gub.BinarySpec, gub.SdkBuildSpec):
    def patch (self):
        self.system ('rm -rf %(srcdir)s/root/usr/include/g++')

def get_cross_packages (settings):
    return (
        Freebsd_runtime (settings).with (version='4.10-2', mirror=download.jantien),
        Binutils (settings).with (version='2.16.1', format='bz2'),
        Gcc (settings).with (version='4.1.0', mirror=download.gcc_41,
                             format='bz2'),
        )


def change_target_packages (packages):
    cross.change_target_packages (packages)
    cross.set_framework_ldpath ([p for p in packages.values ()
                  if isinstance (p, targetpackage.TargetBuildSpec)])

# FIXME: download from sane place.
def get_sdk():
    '''

#FIXME: how to get libc+kernel headers package contents on freebsd?
# * remove zlib.h, zconf.h or include libz and remove Zlib from src packages?
# * remove gmp.h, or include libgmp and remove Gmp from src packages?
# bumb version number by hand, sync with freebsd.py
freebsd-runtime:
	ssh xs4all.nl tar -C / --exclude=zlib.h --exclude=zconf.h --exclude=gmp.h -czf public_html/freebsd-runtime-4.10-2.tar.gz /usr/lib/{lib{c,c_r,m}{.a,.so{,.*}},crt{i,n,1}.o} /usr/include

    '''
