import os
import re

from new import classobj
from new import instancemethod
#
import cross
import download
import gub
import gup
import mingw
import misc

# FIXME: setting binutil's tooldir and/or gcc's gcc_tooldir may fix
# -luser32 (ie -L .../w32api/) problem without having to set LDFLAGS.
class Binutils (cross.Binutils):
    def makeflags (self):
        return misc.join_lines ('''
tooldir="%(cross_prefix)s/%(target_architecture)s"
''')
    def compile_command (self):
        return (cross.Binutils.compile_command (self)
                + self.makeflags ())
    def configure_command (self):
        return ( cross.Binutils.configure_command (self)
                 + ' --disable-werror ')

class W32api_in_usr_lib (gub.BinarySpec, gub.SdkBuildSpec):
    def get_build_dependencies (self):
        return ['w32api']
    def do_download (self):
        pass
    def untar (self):
        self.system ('mkdir -p %(srcdir)s/root/usr/lib')
        self.system ('''
tar -C %(system_root)s/usr/lib/w32api -cf- . | tar -C %(srcdir)s/root/usr/lib -xf-
''')

class Libtool_fixup (gub.NullBuildSpec):
    def get_build_dependencies (self):
        return ['libtool']
    def untar (self):
        self.file_sub ([('/usr/bin/sed', '/bin/sed')],
                       '%(system_root)s/usr/bin/libtool')

class Gcc (mingw.Gcc):
    def get_build_dependencies (self):
        return (mingw.Gcc.get_build_dependencies (self)
                + ['cygwin', 'w32api-in-usr-lib'])
    def makeflags (self):
        return misc.join_lines ('''
tooldir="%(cross_prefix)s/%(target_architecture)s"
gcc_tooldir="%(cross_prefix)s/%(target_architecture)s"
''')
    def compile_command (self):
        return (mingw.Gcc.compile_command (self)
                + self.makeflags ())

    def configure_command (self):
        return (mingw.Gcc.configure_command (self)
                + misc.join_lines ('''
--with-newlib
--enable-threads
'''))

class Gcc_core (Gcc):
    def untar (self):
        gxx_file_name = re.sub ('-core', '-g++',
                                self.expand (self.file_name ()))
        self.untar_cygwin_src_package_variant2 (gxx_file_name, split=True)
        self.untar_cygwin_src_package_variant2 (self.file_name ())

# download-only package
class Gcc_gxx (gub.NullBuildSpec):
    pass

mirror = 'http://mirrors.kernel.org/sourceware/cygwin'
def get_cross_packages (settings):
    import linux
    cross_packs = [
        Binutils (settings).with (version='2.17', format='bz2'),
        W32api_in_usr_lib (settings).with (version='1.0'),
        Gcc (settings).with (version='4.1.1', mirror=download.gcc_41, format='bz2'),
        linux.Python_config (settings).with (version='2.4.3'),
# FIXME: using the binary libtool package is quite involved, it has
# names of tools hardcoded and wrong (LD, NM, SED, GCC, GREP, ...)
#        Libtool_fixup (settings).with (version='1.0'),
        ]

    return cross_packs


def add_cyg_dll (build_spec, get_subpackage_definitions, extra_arg):
    d = get_subpackage_definitions ()
    k = ''
    if d.has_key (k):
        k = 'runtime'
    d[k].append ('/usr/bin/cyg*dll')
    d[k].append ('/etc/postinstall')
    return d

def change_target_package (package):
    cross.change_target_package (package)

    # FIXME: this does not work (?)
    package.get_build_dependencies \
            = misc.MethodOverrider (package.get_build_dependencies,
                                    lambda d, extra: d + extra,
                                    (['cygwin'],))

    package.get_subpackage_definitions = misc.MethodOverrider (
            package.get_subpackage_definitions, add_cyg_dll).method

    ## TODO : get_dependency_dict
        
    # FIXME: why do cross packages get here too?
    if isinstance (package, cross.CrossToolSpec):
        return package
        
    gub.change_target_dict (package, {
            'DLLTOOL': '%(tool_prefix)sdlltool',
            'DLLWRAP': '%(tool_prefix)sdllwrap',
            'LDFLAGS': '-L%(system_root)s/usr/lib -L%(system_root)s/usr/bin -L%(system_root)s/usr/lib/w32api',
            })

def get_cygwin_package (settings, name, dict):
    cross = [
        'base-passwd', 'bintutils',
        'gcc', 'gcc-core', 'gcc-g++',
        'gcc-mingw', 'gcc-mingw-core', 'gcc-mingw-g++',
        'gcc-runtime', 'gcc-core-runtime',
        ]
    cycle = ['base-passwd']
    # FIXME: this really sucks, should translate or something
    # There also is the problem that gub build-dependencies
    # use unsplit packages.
    guile_source = [
        'guile',
        'guile-devel',
        'libguile17',
        ]
    libtool_source = [
        'libltdl3',
        'libtool',
        'libtool1.5',
        ]
    source = guile_source + libtool_source
    # FIXME: These packages are not needed for [cross] building,
    # but most should stay as distro's final install dependency.
    unneeded = [
        'autoconf', 'autoconf2.13', 'autoconf2.50', 'autoconf2.5',
        'automake', 'automake1.9',
        'ghostscript-base', 'ghostscript-x11',
        '-update-info-dir',
        'libguile12', 'libguile16',
        'libxft', 'libxft1', 'libxft2',
        'libbz2-1',
        'perl',
        'tcltk',
        'x-startup-scripts',
        'xorg-x11-bin-lndir',
        'xorg-x11-etc',
        'xorg-x11-fnts',
        'xorg-x11-libs-data',
        ]
    blacklist = cross + cycle + source + unneeded
    if name in blacklist:
        name += '::blacklisted'
    package_class = classobj (name, (gub.BinarySpec,), {})
    package = package_class (settings)
    package.name_dependencies = []
    if dict.has_key ('requires'):
        deps = re.sub ('\([^\)]*\)', '', dict['requires']).split ()
        deps = [x.strip ().lower ().replace ('_', '-') for x in deps]
        ##print 'gcp: ' + `deps`
        deps = filter (lambda x: x not in blacklist, deps)
        package.name_dependencies = deps

    def get_build_dependencies (self):
        return self.name_dependencies
    package.get_build_dependencies = instancemethod (get_build_dependencies,
                                                     package, package_class)
    package.ball_version = dict['version']
        
    package.url = (mirror + '/'
           + dict['install'].split ()[0])
    package.format = 'bz2'
    return package

## UGH.   should split into parsing  package_file and generating gub specs.
def get_cygwin_packages (settings, package_file):
    dist = 'curr'

    dists = {'test': [], 'curr': [], 'prev' : []}
    chunks = open (package_file).read ().split ('\n\n@ ')
    for i in chunks[1:]:
        lines = i.split ('\n')
        name = lines[0].strip ()
        name = name.lower ()
        packages = dists['curr']
        records = {
            'sdesc': name,
            'version': '0-0',
            'install': 'urg 0 0',
            }
        j = 1
        while j < len (lines) and lines[j].strip ():
            if lines[j][0] == '#':
                j = j + 1
                continue
            elif lines[j][0] == '[':
                packages.append (get_cygwin_package (settings, name,
                                                     records.copy ()))
                packages = dists[lines[j][1:5]]
                j = j + 1
                continue

            try:
                key, value = [x.strip () for x in lines[j].split (': ', 1)]
            except:
                print lines[j], package_file
                raise 'URG'
            if (value.startswith ('"')
              and value.find ('"', 1) == -1):
                while 1:
                    j = j + 1
                    value += '\n' + lines[j]
                    if lines[j].find ('"') != -1:
                        break
            records[key] = value
            j = j + 1
        packages.append (get_cygwin_package (settings, name, records))

    # debug
    names = [p.name () for p in dists[dist]]
    names.sort ()
    return dists[dist]

## FIXME: c&p debian.py
class Dependency_resolver:
    def __init__ (self, settings):
        self.settings = settings
        self.packages = {}
        self.load_packages ()
        
    def grok_setup_ini (self, file):
        for p in get_cygwin_packages (self.settings, file):
            self.packages[p.name ()] = p

    def load_packages (self):
        url = mirror + '/setup.ini'

        # FIXME: download/offline update
        file = self.settings.downloads + '/setup.ini'
        if not os.path.exists (file):
            misc.download_url (url, self.settings.downloads)
            # arg
            # self.file_sub ([('\':"', "':'")], file)
            s = open (file).read ()
            open (file, 'w').write (s.replace ('\':"', "':'"))
        self.grok_setup_ini (file)

        # support one extra local setup.ini, that overrides the default
        local_file = self.settings.uploads + '/cygwin/setup.ini'
        if os.path.exists (local_file):
            self.grok_setup_ini (local_file)

    def get_packages (self):
        return self.packages
        
dependency_resolver = None

def init_dependency_resolver (settings):
    global dependency_resolver
    dependency_resolver = Dependency_resolver (settings)

def get_packages ():
    return dependency_resolver.get_packages ()

gub_to_distro_dict = {
    'expat-devel': ['expat'],
    'fontconfig-runtime' : ['libfontconfig1'],
    'fontconfig-devel' : ['libfontconfig-devel'],
    'freetype' : ['libfreetype26'],
    'freetype-devel' : ['libfreetype2-devel'],
    'gettext' : ['libintl8', 'libintl3'],
    'gmp-devel': ['gmp'],
    'guile-runtime' : ['libguile17', 'libguile12'],
#    'libtool': ['libtool1.5'],
    'libtool-runtime': ['libltdl3'],
    'libiconv-devel': ['libiconv2'],
    'texlive-devel': ['libkpathsea4'],
    'pango': ['pango-runtime'],
    'python-devel': ['python'],
    'python-runtime': ['python'],
    }
