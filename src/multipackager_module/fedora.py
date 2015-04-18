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
        self.project_release = "1"


    def check_path_in_builds(self,project_path):

        path_list = ["rpmbuild/SPECS","RPM/SPECS","rpm/SPECS","rpmbuild","RPM","rpm"]

        for element in path_list:
            path = os.path.join(project_path,element)
            if os.path.exists(path):
                return path
        return None


    def get_package_name(self,project_path):
        """ Returns the final package name for the project specified, or None if can't be determined yet """

        self.read_specs_data(project_path)

        if (os.path.exists(os.path.join(project_path,"setup.py"))):
            return None

        return "{:s}.{:s}{:s}-{:s}-{:s}.{:s}.rpm".format(self.project_name,self.distro_type,self.distro_name,self.project_version,self.project_release,self.architecture)


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

        self.read_specs_data(self.build_path)

        return False # no error


    def update(self):

        """ Ensures that the chroot environment is updated with the lastest packages """

        # Here, we have for sure the CHROOT environment, but maybe it must be updated
        command = 'yum --update'
        if (0 != self.run_external_program(command)):
            return True # error!!!

        return False


    def read_specs_data(self,working_path):

        self.dependencies = []
        self.dependencies.append("rpm-build")

        if (os.path.exists(os.path.join(working_path,"setup.py"))): # it is a python package
            self.dependencies.append("python3")
            extra = open(os.path.join(working_path,"setup.cfg"))
            rpm_block = False
            for line in extra:
                line = line.strip()
                if line[0] == '[':
                    if line == "[bdist_rpm]":
                        rpm_block = True
                    else:
                        rpm_block = False

                if not rpm_block:
                    continue

                if line[:15] == "build_requires:":
                    deps = line[15:].split(" ")
                    for l in deps:
                        if l == "":
                            continue
                        self.dependencies.append(l)
                    continue
                if line[:5] == "name:":
                    self.project_name = line[5:].strip()
                    continue
                if line[:8] == "version:":
                    self.project_version = line[8:].strip()
                    continue
                if line[:8] == "release:":
                    self.project_release = line[8:].strip()
                    continue
        else:
            specs_path = self.check_path_in_builds(working_path)

            if not (os.path.exists(specs_path)):
                print(_("The project lacks the rpmbuild/SPECS folder. Aborting."))
                return True
            files = os.listdir(specs_path)
            self.final_file = None
            for l in files:
                if len(l) < 5:
                    continue
                if l[-5:] != ".spec":
                    continue
                self.final_file = os.path.join(specs_path,l)
                break;

            if (self.final_file == None):
                print(_("No .spec file found. Aborting."))
                return True

            spec = open(self.final_file,"r")
            for line in spec:
                if line[:14] == "BuildRequires:":
                    self.dependencies.append(line[14:].strip())
                    continue
                if line[:5] == "Name:":
                    self.project_name = line[5:].strip()
                    continue
                if line[:8] == "Version:":
                    self.project_version = line[8:].strip()
                    continue
                if line[:8] == "Release:":
                    self.project_release = line[8:].strip()
                    continue


    def install_build_deps(self):

        """ Install the dependencies needed for building this package """

        if (len(self.dependencies) != 0):
            command = "yum -y install"
            for dep in self.dependencies:
                command += " "+dep
            if (self.run_chroot(self.working_path, command)):
                return True
        return False


    def build_python(self):
        """ Builds a package for a python project """

        if (self.run_chroot(self.working_path, 'bash -c "cd /project && python3 setup.py bdist_rpm"')):
            return True

        return False


    def build_package(self):
        """ Takes the binaries located at /install_root and build a package """

        setup_python = os.path.join(self.build_path,"setup.py")
        if (os.path.exists(setup_python)):
            command = "cp -a {:s} {:s}".format(os.path.join(self.build_path,"dist/*.noarch.rpm"),os.getcwd())
            if (self.run_external_program(command)):
                return True
            return False

        tmpfolder = self.check_path_in_builds(self.build_path)
        if (tmpfolder == None):
            print (_("Can't find the rpmbuild folder. Aborting."))
            return True

        os.makedirs(os.path.join(self.working_path,"rpmpackage/SPECS"))
        os.makedirs(os.path.join(self.working_path,"rpmpackage/SOURCES"))
        os.makedirs(os.path.join(self.working_path,"rpmpackage/BUILD"))
        os.makedirs(os.path.join(self.working_path,"rpmpackage/RPMS"))
        os.makedirs(os.path.join(self.working_path,"rpmpackage/SRPMS"))

        try:
            f = open(os.path.join(self.working_path,"root/.rpmmacros"),"w")
            f.write("%_topdir /rpmpackage\n")
            f.write("%_builddir %{_topdir}/BUILD\n")
            f.write("%_rpmdir %{_topdir}/RPMS\n")
            f.write("%_sourcedir %{_topdir}/SOURCES\n")
            f.write("%_specdir %{_topdir}/SPECS\n")
            f.write("%_srcrpmdir %{_topdir}/SRPMS\n")
            f.close()
        except:
            print (_("Can't create the .rpmmacros file. Aborting."))
            return True

        spec_i = open(self.final_file,"r")
        spec_o = open(os.path.join(self.working_path,"rpmpackage/SPECS",self.project_name+".specs"),"w")
        do_copy = True
        for line in spec_i:
            line = line.strip()
            if (line == ""):
                do_copy = True
                spec_o.write("\n")
                continue

            if do_copy == False:
                continue

            if line[0] != '%':
                spec_o.write(line+"\n")
                continue

            if line[:5] == "%prep":
                spec_o.write("%prep\n")
                do_copy = False
                continue
            if line[:6] == "%build":
                spec_o.write("%build\n")
                do_copy = False
                continue
            if line[:8] == "%install":
                spec_o.write("%install\n")
                spec_o.write("rm -rf $RPM_BUILD_ROOT/*\n")
                spec_o.write("cp -a /install_root/* $RPM_BUILD_ROOT/\n")
                do_copy = False
                continue
            if line[:6] == "%clean":
                spec_o.write("%clean\n")
                spec_o.write("rm -rf $RPM_BUILD_ROOT/*\n")
                do_copy = False
                continue
            if line[:6] == "%files":
                spec_o.write("%files\n")
                spec_o.write("/*\n")
                do_copy = False
                continue

            spec_o.write(line+"\n")
        spec_i.close()
        spec_o.close()

        command = "rpmbuild -bb {:s}".format(os.path.join("rpmpackage/SPECS",self.project_name+".specs"))
        if (self.run_chroot(self.working_path, command)):
            return True

        command = "cp -a {:s} {:s}".format(os.path.join(self.working_path,"rpmpackage/RPMS/*"),os.path.join(os.getcwd(),self.get_package_name(self.build_path)))
        if (self.run_external_program(command)):
            return True

        return False

