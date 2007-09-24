import glob
import os
import re

from gub import mirrors
from gub import misc
from gub import targetpackage

class Pango (targetpackage.TargetBuildSpec):
    def __init__ (self, settings):
        targetpackage.TargetBuildSpec.__init__ (self, settings)
        self.with_template (version='1.14.8',
                   mirror=mirrors.gnome_216,
                   format='bz2')

    def get_build_dependencies (self):
        return ['freetype-devel', 'fontconfig-devel', 'glib-devel',
                'libtool']

    def get_dependency_dict (self):
        return {'': ['freetype', 'fontconfig', 'glib', 'libtool-runtime']}


    def configure_flags (self):
        return misc.join_lines ('''
--without-x
--without-cairo
''')

    def configure_command (self):
        return (targetpackage.TargetBuildSpec.configure_command (self)
                + self.configure_flags ())

    def configure (self):
        targetpackage.TargetBuildSpec.configure (self)                
        self.update_libtool ()

    def patch (self):
        targetpackage.TargetBuildSpec.patch (self)
        self.system ('cd %(srcdir)s && patch --force -p1 < %(patchdir)s/pango-substitute-env.patch')

    def fix_modules (self, prefix='/usr'):
        etc = self.expand ('%(install_root)s/%(prefix)s/etc/pango', locals ())
        self.system ('mkdir -p %(etc)s' , locals ())

        self.map_locate (lambda x: self.file_sub ([('/%(prefix)s/',
                                                    '$PANGO_PREFIX/')], x,
                                                  locals ()), etc, '*')

        self.pango_module_version = None
        def write_pangorc (dir):
            if self.pango_module_version:
                return
            m = re.search ('([0-9.]+)', dir)
            if m:
                #FIXME: circumvent SetAttrTooLate arg.
                self.__dict__['pango_module_version'] = m.group (1)
                open (etc + '/pangorc', 'w').write ('''[Pango]
ModuleFiles = $PANGO_PREFIX/etc/pango/pango.modules
ModulesPath = $PANGO_PREFIX/lib/pango/%(pango_module_version)s/modules
''' % self.__dict__)
        
        self.map_locate (write_pangorc, '%%(install_root)s/%(prefix)s/lib/pango' % locals (), '*')

        def check_pango_module_version ():
            assert (self.pango_module_version)
        self.os_interface.func (check_pango_module_version)
        self.copy ('%(sourcefiledir)s/pango.modules', etc)

    def install (self):
        targetpackage.TargetBuildSpec.install (self)                
        self.dump ("""
setfile PANGO_RC_FILE=$INSTALLER_PREFIX/etc/pango/pangorc
setdir PANGO_PREFIX=$INSTALLER_PREFIX/
""", '%(install_prefix)s/etc/relocate/pango.reloc', env=locals())
        self.fix_modules ()

class Pango__linux (Pango):
    def untar (self):
        Pango.untar (self)
        # FIXME: --without-cairo switch is removed in 1.10.1,
        # pango only compiles without cairo if cairo is not
        # installed linkably on the build system.  UGH.
        self.file_sub ([('(have_cairo[_a-z0-9]*)=true', '\\1=false'),
                        ('(cairo[_a-z0-9]*)=yes', '\\1=no')],
                       '%(srcdir)s/configure')

class Pango__freebsd (Pango__linux):
    def get_build_dependencies (self):
        return Pango__linux.get_build_dependencies (self) + ['libiconv-devel']
            

class Pango__darwin (Pango):
    def configure (self):
        Pango.configure (self)
        self.file_sub ([('nmedit', '%(target_architecture)s-nmedit')],
                       '%(builddir)s/libtool')

    def install (self):
        Pango.install (self)                
        self.dump ("""
set PANGO_SO_EXTENSION=.so
""", '%(install_prefix)s/etc/relocate/pango.reloc', env=locals(), mode="a")
