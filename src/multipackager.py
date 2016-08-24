#!/usr/bin/env python3

# Copyright 2015 (C) Raster Software Vigo (Sergio Costas)
#
# This file is part of Multipackager
#
# Multipackager is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Multipackager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import sys
import os
import gettext
import locale
import configparser
import fnmatch
import multipackager_module.debian
import multipackager_module.fedora
import multipackager_module.arch
import multipackager_module.configuration
import multipackager_module.package_base

import pkg_resources

gettext.bindtextdomain("multipackager","/usr/share/locale")
try:
    locale.setlocale(locale.LC_ALL,"")
except locale.Error:
    pass
gettext.textdomain("multipackager")
gettext.install("multipackager","/usr/share/locale")

_ = gettext.gettext

version = str(pkg_resources.require("multipackager")[0].version)

def print_usage(doexit = True):

    global version

    print ("Multipackager")
    print ("Version {:s}".format(version))
    print ("Usage:")
    print ("multipackager.py [--config config_file] [-r|--revision revision_number] [--noclean] project_folder")
    print ("multipackager.py [--config config_file] [-r|--revision revision_number] [--noclean] project_folder {debian|ubuntu|fedora|arch} version_name {i386|amd64}")
    print ("multipackager.py [--config config_file] shell vm_folder {i386|amd64}")
    print ("multipackager.py [--config config_file] shell vm_folder {debian|ubuntu|fedora|arch} version_name {i386|amd64}")
    print ("multipackager.py [--config config_file] update")
    print ("multipackager.py [--config config_file] update {debian|ubuntu|fedora|arch} version_name {i386|amd64}")
    print ("multipackager.py [--config config_file] clearcache")
    print ("multipackager.py [--config config_file] clearcache {debian|ubuntu|fedora|arch} version_name {i386|amd64}")

    if (doexit):
        sys.exit(-1)


if (os.geteuid() != 0):
    print_usage(False)
    print(_("\nThis program must be run as root\n"))
    sys.exit(-1)


def get_distro_object(distro_name):

    if (distro_name == "debian") or (distro_name == "ubuntu"):
        return multipackager_module.debian.debian

    if (distro_name == "fedora"):
        return multipackager_module.fedora.fedora

    if (distro_name == "arch"):
        return multipackager_module.arch.arch

    print(_("Distro name {:s} unknown. Aborting.").format(distro_name))
    sys.exit(-1)

    return None


def get_most_recent(filepath):
    
    path,fname = os.path.split(filepath)
    if (path == None) or (path == ""):
        path = "."
    last_date = 0
    final_file = None
    for element in os.listdir(path):
        fullpath = os.path.join(path,element)
        if os.path.isdir(fullpath):
            continue
        if os.path.islink(fullpath):
            continue
        cdate = os.path.getmtime(fullpath)
        if (fnmatch.fnmatch(element,fname)) and (cdate > last_date):
            final_file = fullpath
            last_date = cdate

    return final_file


def build_project(config,project_path):

    """ This function does all the work """

    built = []
    skipped = []
    failed = []

    if (os.path.exists(os.path.join(project_path,"setup.py"))):
        is_python = True
    else:
        is_python = False

    preinstall = {}
    dont_install = {}

    cfg = os.path.join(project_path,"multipackager.conf")
    config_local = configparser.ConfigParser(allow_no_value=True)
    if os.path.exists(cfg):
        config_local.read(cfg)
        # check the packages to preinstall in each case
        for element_i in config_local.sections():
            element = config_local[element_i]
            list_packages = []
            dont_install_p = []
            for package_r in element:
                f = get_most_recent(element[package_r])
                if f == None:
                    continue
                list_packages.append(f)
                dont_install_p.append(package_r)
            if len(list_packages) != 0:
                while element_i.find("  ") != -1:
                    print(element_i)
                    element_i = element_i.replace("  "," ")
                preinstall[element_i] = list_packages
                dont_install[element_i] = dont_install_p


    for element in config.distros:

        if ((is_python) and (element["type"] == "binary")) or ((not is_python) and (element["type"] == "python")):
            continue

        distroclass = get_distro_object(element["distro"])
        sys.stdout.write("\x1b]2;"+_("Compiling for {:s} {:s}, {:s}").format(element["distro"],element["name"],element["architecture"])+"\x07")
        # create a DISTRO object of the right type
        distro = distroclass(config,element["distro"],element["name"],element["architecture"],"builder")

        package_name = distro.get_package_name(project_path)

        if (package_name == True):
            failed.append(_("Can't get the package name for distro {:s}").format(distro.distro_full_name))
            continue
        if (package_name != None) and (os.path.exists(os.path.join(os.getcwd(),package_name))):
            skipped.append(package_name)
            continue

        # copy the environment to a working folder
        if distro.check_environment():
            failed.append(_("Can't create working environment for package {:s} in distro {:s}").format(package_name,distro.distro_full_name))
            continue

        # install the packages needed for building the project
        if distro.distro_full_name in dont_install:
            avoid_packages = dont_install[distro.distro_full_name]
        else:
            avoid_packages = []

        if (not distro.install_dependencies(project_path,avoid_packages,preinstall)):
            if distro.prepare_working_path_overlay():
                failed.append(_("Can't prepare the working path inside the distro {:s} for package {:s}").format(distro.distro_full_name,package_name))
                if config.clean:
                    distro.cleanup()
                continue
            had_error = False

            if not distro.install_postdependencies(project_path):
                if distro.distro_full_name in preinstall:
                    for package in preinstall[distro.distro_full_name]:
                        print(_("Installing package {:s}").format(package))
                        if distro.install_local_package(package):
                            had_error = True
                            failed.append(_("Can't install package {:s} in the distro {:s}").format(package,distro.distro_full_name))
                # build the project itself
                if (not had_error) and (not distro.build_project(project_path)):
                    distro.get_project_size()
                    # if there are no errors, create the package and copy it to the current directory
                    if distro.build_package(project_path):
                        failed.append(_("Can't build the package {:s} in the distro {:s}").format(package_name,distro.distro_full_name))
                        if config.clean:
                            distro.cleanup()
                        continue
                    if package_name != None:
                        built.append(package_name)

        # remove temporary data
        if config.clean:
            distro.cleanup()

    if len(built) > 0:
        print(_("Built packages:"))
        for l in built:
            print(l)
    else:
        print(_("Built packages: None"))
    if len(skipped) > 0:
        print(_("Skipped packages:"))
        for l in skipped:
            print(l)
    else:
        print(_("Skipped packages: none"))
    if len(failed) > 0:
        print(_("Failed packages:"))
        for l in failed:
            print(l)
    else:
        print(_("Failed packages: none"))


def launch_shell(argv,config):

    nparams = len(argv)
    if (nparams != 4) and (nparams != 6):
        print_usage()

    env_path = argv[2]

    config.set_project_path(env_path)
    if (config.read_config_file()):
        sys.exit(-1)

    if nparams == 4:
        if not os.path.exists(env_path):
            print (_("The specified CHROOT environment at {:s} doesn't exists. Aborting.").format(env_path))
            sys.exit(-1)
        arch = argv[3]
        dtype = ""
        name = ""
        distro = multipackager_module.package_base.package_base(config,dtype,name,arch)
        distro.working_path = env_path
    else:
        dtype = argv[3]
        name = argv[4]
        arch = argv[5]
        distroclass = get_distro_object(dtype)
        # create a DISTRO object of the right type
        distro = distroclass(config,dtype,name,arch)
        if distro.check_environment():
            sys.exit(-1)

    if not os.path.exists(env_path):
        distro.prepare_working_path(env_path)
    else:
        distro.working_path = env_path
        if (nparams != 3):
            print(_("The project folder exists; launching the shell without copying data"))

    sys.stdout.write("\x1b]2;"+_("Launched shell at {:s}").format(env_path)+"\x07")
    command = ""
    for path in config.mount_path:
        command += "--bind={:s} ".format(path)
    command += config.shell
    distro.run_chroot(env_path, command)


def update_envs(argv,config):

    nparams = len(argv)

    if (nparams != 2) and (nparams != 5):
        print_usage()

    retval = config.read_config_file()
    if (retval):
        sys.exit(-1)

    if (nparams == 5):
        retval = config.read_config_file()
        config.delete_distros()
        config.append_distro(sys.argv[2], sys.argv[3] ,sys.argv[4])
        retval = False

    updated = []

    for element in config.distros:

        found = False
        for l in updated:
            if (l["distro"] == element["distro"]) and (l["name"] == element["name"]) and (l["architecture"] == element["architecture"]):
                found = True
                break
        if found:
            continue

        updated.append(element)

        distroclass = get_distro_object(element["distro"])

        # create a DISTRO object of the right type
        distro = distroclass(config,element["distro"],element["name"],element["architecture"],"builder")
        if distro.check_environment():
            continue
        # update the packages in the cached environment
        distro.update_environment()


def clearcache(argv,config):

    nparams = len(argv)

    if (nparams != 2) and (nparams != 5):
        print_usage()

    retval = config.read_config_file()
    if (retval):
        sys.exit(-1)

    if (nparams == 5):
        retval = config.read_config_file()
        config.delete_distros()
        config.append_distro(sys.argv[2], sys.argv[3] ,sys.argv[4])
        retval = False

    for element in config.distros:

        distroclass = get_distro_object(element["distro"])

        # create a DISTRO object of the right type
        distro = distroclass(config,element["distro"],element["name"],element["architecture"],"builder")
        # update the packages in the cached environment
        distro.clear_cache()


config = multipackager_module.configuration.configuration()

args = config.parse_args(sys.argv)
if args == None:
    print_usage()

if (len(args) == 1) or (args[1] == "help") or (args[1] == "version"):
    print_usage()

if (args[1] == "shell"):
    launch_shell(args,config)
    sys.exit(0)

if (args[1] == "update"):
    update_envs(args,config)
    sys.exit(0)

if (args[1] == "clearcache"):
    clearcache(args,config)
    sys.exit(0)

try:
    os.makedirs(config.working_path)
except:
    pass
try:
    os.makedirs(config.cache_path)
except:
    pass

nparams = len(args)

if (nparams != 2) and (nparams != 5):
    print_usage()

project_folder = args[1]
config.set_project_path(project_folder)

if config.read_config_file():
    sys.exit(-1)

if (nparams == 5):
    # read all the configuration to set all the parameters
    retval = config.read_config_file()
    config.delete_distros()
    config.append_distro(args[2], args[3] ,args[4])
    retval = False

build_project(config,project_folder)
