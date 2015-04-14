#!/usr/bin/env python3

import os
from glob import glob
from distutils.core import setup
from distutils import dep_util

def get_data_files():
    data_files = [
        #(os.path.join('share', 'doc','multipackager'), ['doc']),
        (os.path.join('share', 'man','man1'), ['multipackager.1']),
    ]

    for lang_name in [f for f in os.listdir('locale')]:
        mofile = os.path.join('locale', lang_name,'LC_MESSAGES','multipackager.mo')
        # translations must be always in /usr/share because Gtk.builder only search there. If someone knows how to fix this...
        target = os.path.join('/usr','share', 'locale', lang_name, 'LC_MESSAGES') # share/locale/fr/LC_MESSAGES/
        data_files.append((target, [mofile]))

    return data_files


def compile_translations():

    try:
        for pofile in [f for f in os.listdir('po') if f.endswith('.po')]:
            pofile = os.path.join('po', pofile)

            lang = os.path.basename(pofile)[:-3] # len('.po') == 3
            modir = os.path.join('locale', lang, 'LC_MESSAGES') # e.g. locale/fr/LC_MESSAGES/
            mofile = os.path.join(modir, 'multipackager.mo') # e.g. locale/fr/LC_MESSAGES/multipackager.mo

            # create an architecture for these locales
            if not os.path.isdir(modir):
                os.makedirs(modir)

            if not os.path.isfile(mofile) or dep_util.newer(pofile, mofile):
                print('compiling %s' % mofile)
                # msgfmt.make(pofile, mofile)
                os.system("msgfmt \"" + pofile + "\" -o \"" + mofile + "\"")
            else:
                print('skipping %s - up to date' % mofile)
    except:
        pass

compile_translations()

os.system("pandoc -s -f markdown_github -t man -o multipackager.1 README.md")

current_version = "0.2"

config_data = open("src/multipackager.py","r")
for line in config_data:
    line = line.strip()
    if (line.startswith("version =")):
        pos = line.find('"')
        if pos == -1:
            continue
        current_version = line[pos+1:-1].replace(" ","").lower().replace("beta",".beta")
        break
config_data.close()

#here = os.path.abspath(os.path.dirname(__file__))

setup(
    name='multipackager_module',

    version=current_version,

    description='Simplifies the creation of Linux packages for multiple architectures and distributions.',
    long_description = "A tool to create packages for mutiple architectures and linux OS",

    url='http://www.rastersoft.com',

    author='Raster Software Vigo (Sergio Costas)',
    author_email='raster@rastersoft.com',

    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        # 1 - Planning
        # 2 - Pre-Alpha
        # 3 - Alpha
        # 4 - Beta
        # 5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3'
    ],

    keywords='package deb',

    packages=['multipackager_module'],

    package_dir={"multipackager_module" : "src/multipackager_module"},

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages.
    # see http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    data_files = get_data_files(),
    scripts=['src/multipackager.py'],
)
