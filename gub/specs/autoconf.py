from gub import tools

class Autoconf__tools (tools.AutoBuild):
    source = 'http://ftp.gnu.org/pub/gnu/autoconf/autoconf-2.63.tar.gz'
    parallel_build_broken = True
    dependencies = [
            'm4',
            'perl',
            ]
    # prevent execution of Emacs to build .elc files
    configure_variables = (tools.AutoBuild.configure_variables
                           + ' EMACS=false')
