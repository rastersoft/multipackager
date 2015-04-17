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
import multipackager_module.debian
import multipackager_module.configuration
import multipackager_module.package_base

gettext.bindtextdomain("multipackager","/usr/share/locale")
try:
    locale.setlocale(locale.LC_ALL,"")
except locale.Error:
    pass
gettext.textdomain("multipackager")
gettext.install("multipackager","/usr/share/locale")

_ = gettext.gettext

version = "0.5"


def print_usage(doexit = True):

    global version

    print ("Multipackager")
    print ("Version {:s}".format(version))
    print ("Usage:")
    print ("multipackager.py project_folder [--config config_file]")
    print ("multipackager.py project_folder [--config config_file] {debian|ubuntu} version_name {i386|amd64}")
    print ("multipackager.py shell [--config config_file] vm_folder {i386|amd64}")
    print ("multipackager.py shell [--config config_file] vm_folder {debian|ubuntu} version_name {i386|amd64}")
    print ("multipackager.py update [--config config_file]")
    print ("multipackager.py update [--config config_file] {debian|ubuntu} version_name {i386|amd64}")

    if (doexit):
        sys.exit(-1)


if (os.geteuid() != 0):
    print_usage(False)
    print(_("\nThis program must be run as root\n"))
    sys.exit(-1)


def get_distro_object(distro_name):

    if (distro_name == "debian") or (distro_name == "ubuntu"):
        return multipackager_module.debian.debian

    print(_("Distro name {:s} unknown. Aborting.").format(distro_name))
    sys.exit(-1)

    return None


def build_project(config,project_path):

    """ This function does all the work """

    built = []
    skipped = []

    for element in config.distros:
        distroclass = get_distro_object(element["distro"])

        # create a DISTRO object of the right type
        distro = distroclass(config,element["distro"],element["name"],element["architecture"])

        package_name = distro.get_package_name(project_path)
        if (package_name == True):
            print("Can't get the package name")
            sys.exit(-1)

        if (package_name != None) and (os.path.exists(os.path.join(os.getcwd(),package_name))):
            skipped.append(package_name)
            continue

        # copy the environment to a working folder
        if (distro.prepare_environment()):
            print (_("Error when creating the working environment"))
            sys.exit(-1)
        # install the packages needed for building the project, and build it
        if (not distro.build_project(project_path)):
            # if there are no errors, create the package and copy it to the current directory
            if distro.build_package():
                sys.exit(-1)
            built.append(package_name)
        # remove temporary data
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
    else:
        dtype = argv[3]
        name = argv[4]
        arch = argv[5]
        distroclass = get_distro_object(dtype)
        # create a DISTRO object of the right type
        distro = distroclass(config,dtype,name,arch)

    if not os.path.exists(env_path):
        distro.copy_environment(env_path)
    else:
        if (nparams != 3):
            print(_("The project folder exists; launching the shell without copying data"))

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

    for element in config.distros:
        distroclass = get_distro_object(element["distro"])

        # create a DISTRO object of the right type
        distro = distroclass(config,element["distro"],element["name"],element["architecture"])
        # update the packages in the cached environment
        distro.update_environment()


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

nparams = len(args)

if (nparams != 2) and (nparams != 5):
    print_usage()

project_folder = sys.argv[1]
config.set_project_path(project_folder)

if config.read_config_file():
    sys.exit(-1)

if (nparams == 5):
    # read all the configuration to set all the parameters
    retval = config.read_config_file()
    config.delete_distros()
    config.append_distro(sys.argv[2], sys.argv[3] ,sys.argv[4])
    retval = False

build_project(config,project_folder)