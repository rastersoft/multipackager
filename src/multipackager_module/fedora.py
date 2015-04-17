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


import os
import shutil
import multipackager_module.package_base

class fedora (multipackager_module.package_base.package_base):

    def __init__(self, configuration, distro_type, distro_name, architecture):

        multipackager_module.package_base.package_base.__init__(self, configuration, distro_type, distro_name, architecture)
        self.project_name = "project"
        self.project_version = "1.0"


    def check_path_in_builds(self,project_path):

        if self.distro_type == "ubuntu":
            # Try the "ubuntu" folder, and if it doesn't exists, try with "fedora" one
            path_list = ["ubuntu","UBUNTU","Ubuntu","debian","DEBIAN","Debian"]
        else:
            path_list = ["debian","DEBIAN","Debian"]

        for element in path_list:
            path = os.path.join(project_path,element)
            if os.path.exists(path):
                return path
        return None


    def get_package_name(self,project_path):
        """ Returns the final package name for the project specified, or None if can't be determined yet """

        if (os.path.exists(os.path.join(project_path,"setup.py"))):
            return None

        return None


    def generate(self):
        """ Ensures that the base system, to create a CHROOT environment, exists """

        # Create all, first, in a temporal folder
        tmp_path = self.base_path+".tmp"

        shutil.rmtree(tmp_path, ignore_errors=True)

        os.makedirs(tmp_path)

        yumcfgpath = os.path.join(tmp_path,"yum.conf")
        yumrepospath = os.path.join(tmp_path,"yum.repos.d")
        os.makedirs(yumrepospath)

        yumcfg = open(yumcfgpath,"w")
        yumcfg.write("[main]\n")
        yumcfg.write("cachedir=/var/cache/yum\n")
        yumcfg.write("persistdir=/var/lib/yum\n")
        yumcfg.write("keepcache=0\n")
        yumcfg.write("debuglevel=2\n")
        yumcfg.write("logfile={:s}\n".format(os.path.join(tmp_path,"build.log")))
        yumcfg.write("exactarch=0\n")
        yumcfg.write("obsoletes=1\n")
        yumcfg.write("gpgcheck=1\n")
        yumcfg.write("plugins=1\n")
        yumcfg.write("installonly_limit=3\n")
        yumcfg.write("reposdir={:s}\n".format(yumrepospath))
        yumcfg.close()

        yumrepos = open(os.path.join(yumrepospath,"fedora.repo"),"w")
        yumrepos.write("[fedora]\n")
        yumrepos.write("name=Fedora {:s} - {:s}\n".format(self.distro_name,self.architecture))
        yumrepos.write("failovermethod=priority\n")
        yumrepos.write("metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-{:s}&arch={:s}\n".format(self.distro_name,self.architecture))
        yumrepos.write("enabled=1\n")
        yumrepos.write("medatada_expire=7d\n")
        yumrepos.write("gpgcheck=1\n")
        yumrepos.write("gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-{:s}-{:s}\n".format(self.distro_name,self.architecture))
        yumrepos.write("skip_if_unavailable=False\n")
        yumrepos.close()

        os.makedirs(os.path.join(tmp_path,"var","lib","rpm"))

        command = "yum -y --config={:s} --releasever={:s} --nogpg --installroot={:s} --disablerepo='*' --enablerepo=fedora install fedora-release bash yum".format(yumcfgpath,self.distro_name,tmp_path)
        if (0 != self.run_external_program(command)):
            shutil.rmtree(tmp_path, ignore_errors=True)
            return True # error!!!

        shutil.rmtree(yumrepospath)
        os.remove(yumcfgpath)

        # for some reason, the RPM database is not complete, so it is a must to reinstall everything from inside the chroot environment
        # umount /sys to avoid failure due to filesystem.rpm
        command = 'bash -c "umount /sys && yum -y --releasever={:s} install fedora-release bash yum"'.format(self.distro_name)
        self.run_chroot(tmp_path, command)

        os.sync()
        os.rename(tmp_path,self.base_path) # rename the folder to the definitive name
        os.sync()

        shutil.rmtree(tmp_path, ignore_errors=True)

        return False # no error


    def update(self):

        """ Ensures that the chroot environment is updated with the lastest packages """

        # Here, we have for sure the CHROOT environment, but maybe it must be updated
        command = 'yum --update'
        if (0 != self.run_external_program(command)):
            return True # error!!!

        return False


    def install_build_deps(self):

        """ Install the dependencies needed for building this package """

        dependencies = []

        if (os.path.exists(os.path.join(self.build_path,"setup.py"))): # it is a python package
            dependencies.append("python3")
        else:
            return True

        if (len(dependencies) != 0):
            command = ""
            for dep in dependencies:
                command += " "+dep
            if (self.run_chroot(self.working_path, command)):
                return True
        return False


    def build_python(self):
        """ Builds a package for a python project """

        return True


    def build_package(self):
        """ Takes the binaries located at /install_root and build a package """

        setup_python = os.path.join(self.build_path,"setup.py")
        if (os.path.exists(setup_python)):
            # it is a python project
            return True

        return True

