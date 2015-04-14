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


import subprocess
import os
import shutil

class package_base(object):

    def __init__(self, configuration, distro_type, distro_name, architecture):

        self.configuration = configuration
        self.distro_type = distro_type
        self.distro_name = distro_name
        self.architecture = architecture

        # name of the CHROOT environment to use
        self.chroot_name = self.distro_type+"_chroot_"+self.distro_name+"_"+self.architecture

        # path of the base CHROOT enviromnent to use
        self.base_path = os.path.join(self.configuration.cache_path,self.chroot_name)

        if (self.base_path[-1] == os.path.sep):
            self.base_path = self.base_path[:-1] # remove the last "/" if it exists

        # path of the working copy
        self.working_path = None

        # path of the project copy (outside the chroot environment; inside is always "/project")
        self.build_path = None


    def update_environment(self):

        """ Ensures that the environment is updated with the last packages """

        backup_path = self.base_path+".backup"

        # If there is no base system, create it
        if (not os.path.exists(self.base_path)):
            print(_("Generating the environment for {:s}").format(self.chroot_name))
            if self.generate():
                return True # error!!!

        print(_("Generating a backup for {:s}").format(self.chroot_name))
        shutil.rmtree(backup_path, ignore_errors=True) # delete any backup that already exists
        if (0 != self.run_external_program("cp -a {:s} {:s}".format(self.base_path,backup_path))): # do a backup of the base system, just in case the update fails
            shutil.rmtree(backup_path, ignore_errors=True)
            return True # error!!!

        os.sync() # sync disks
        # Add OpenDNS
        f = open(os.path.join(self.base_path,"etc","resolv.conf"),"w")
        f.write("# OpenDNS IPv4 nameservers\nnameserver 208.67.222.222\nnameserver 208.67.220.220\n# OpenDNS IPv6 nameservers\nnameserver 2620:0:ccc::2\nnameserver 2620:0:ccd::2\n")
        f.close()

        print(_("Updating {:s}").format(self.chroot_name))
        if (self.update()): # error when updating!!! restore backup
            shutil.rmtree(self.base_path, ignore_errors=True)
            os.rename(backup_path,self.base_path) # rename the backup folder to the definitive name
            os.sync() # sync disks
            return True # error!

        os.sync() # sync disks
        shutil.rmtree(backup_path, ignore_errors=True)

        return False


    def prepare_environment(self):

        """ Creates a working copy of the chroot environment to keep the original untouched """

        print(_("Creating working copy of {:s}").format(self.chroot_name))
        if (not os.path.exists(self.configuration.working_path)):
            os.makedirs(self.configuration.working_path)

        shutil.rmtree(os.path.join(self.configuration.working_path,self.chroot_name), ignore_errors=True)
        if (0 != self.run_external_program("cp -a {:s} {:s}".format(self.base_path,self.configuration.working_path))): # copy the base system to the path where we want to work with to generate the package
            return True # error!!!

        self.working_path = os.path.join(self.configuration.working_path,self.chroot_name)
        # environment ready
        return False


    def copy_environment(self,final_path):

        """ Creates a working copy of the chroot environment to keep the original untouched """

        print(_("Creating working copy of {:s}").format(self.chroot_name))
        if (not os.path.exists(final_path)):
            os.makedirs(final_path)

        if (0 != self.run_external_program("rm -rf {:s}".format(os.path.join(final_path,"*")))):
            return True
        if (0 != self.run_external_program("cp -a {:s} {:s}".format(os.path.join(self.base_path,"*"),final_path))): # copy the base system to the path where we want to work with to generate the package
            return True # error!!!

        return False


    def build_project(self,project_path):

        """ Builds the specified project inside the working copy of the chroot environment """

        self.build_path = os.path.join(self.working_path,"project")

        os.makedirs(self.build_path)

        # copy the project folder inside the CHROOT environment, in the "/project" folder

        if (0 != self.run_external_program("cp -a {:s} {:s}".format(os.path.join(project_path,"*"),os.path.join(self.working_path,"project/")))):
            return True # error!!!

        # install the building dependencies

        if (self.install_build_deps()):
            return True # error!!!

        # the compiled binaries will be installed in /install_root, inside the chroot environment
        install_path = os.path.join(self.working_path,"install_root")
        shutil.rmtree(install_path, ignore_errors = True)
        os.makedirs (install_path)

        specific_creator = "multipackager_{:s}.sh".format(self.distro_type)
        # check the install system available
            # First, check if exists a shell file called 'multipackager_DISTROTYPE.sh' (like multipackager_debian.sh, or multipackager_ubuntu.sh)
        if (os.path.exists(os.path.join(self.build_path,specific_creator))):
            return self.build_multipackager(specific_creator)
            # Now check if it exists a generic shell script called 'multipackager.sh'
        elif (os.path.exists(os.path.join(self.build_path,"multipackager.sh"))):
            return self.build_multipackager("multipackager.sh")
            # Check if it is an autoconf/automake with the 'configure' file already generated
        elif (os.path.exists(os.path.join(self.build_path,"configure"))):
            return self.build_autoconf(False)
            # Now check if it is an autoconf/automake without the 'configure' file generated
        elif (os.path.exists(os.path.join(self.build_path,"autogen.sh"))):
            return self.build_autoconf(True)
            # Check if it is a CMake project
        elif (os.path.exists(os.path.join(self.build_path,"CMakeLists.txt"))):
            return self.build_cmake()
            # Finally, try with a classic Makefile
        elif (os.path.exists(os.path.join(self.build_path,"Makefile"))):
            return self.build_makefile()

        print (_("Unknown build system"))
        return True


    def build_multipackager(self,filename):

        return self.run_chroot(self.working_path, 'bash -c "cd /project && source {:s}"'.format(filename))


    def build_cmake(self):

        install_path = os.path.join(self.build_path,"install")
        if (os.path.exists(install_path)):
            shutil.rmtree(install_path,ignore_errors = True)
        os.makedirs(install_path)

        return self.run_chroot(self.working_path, 'bash -c "cd /project/install && cmake .. -DCMAKE_INSTALL_PREFIX=/usr && make && make DESTDIR=/install_root install"')


    def build_autoconf(self,autogen):

        if (autogen):
            if (self.run_chroot(self.working_path, 'bash -c "cd /project && ./autogen.sh"')):
                return True

        return self.run_chroot(self.working_path, 'bash -c "cd /project && ./configure --prefix=/usr && make && make DESTDIR=/install_root install"')


    def build_makefile(self):

        return self.run_chroot(self.working_path, 'bash -c "cd /project && make && make PREFIX=/usr DESTDIR=/install_root install"')


    def cleanup(self):

        shutil.rmtree(self.working_path)
        return False


    def run_external_program(self,command):

        print(_("Launching {:s}").format(str(command)))
        proc = subprocess.Popen(command, shell=True)
        return proc.wait()


    def run_chroot(self,base_path,command):

        if self.architecture == "i386":
            personality = "x86"
        else:
            personality = "x86-64"

        command = "systemd-nspawn -D {:s} --personality {:s} {:s}".format(base_path,personality,command)
        return self.run_external_program(command)

