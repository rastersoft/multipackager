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
import configparser
import multipackager_module.package_base

class fedora (multipackager_module.package_base.package_base):

    def __init__(self, configuration, distro_type, distro_name, architecture, cache_name = None):

        if architecture == "amd64":
            architecture = "x86_64"

        multipackager_module.package_base.package_base.__init__(self, configuration, distro_type, distro_name, architecture,cache_name)
        self.distro_number = int(self.distro_name)


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

        if os.path.exists(os.path.join(project_path,"setup.py")):
            return "{:s}.{:s}{:s}-{:s}-{:d}.noarch.rpm".format(self.project_name,self.distro_type,self.distro_name,self.project_version,self.configuration.revision)
        else:
            return "{:s}.{:s}{:s}-{:s}-{:d}.{:s}.rpm".format(self.project_name,self.distro_type,self.distro_name,self.project_version,self.configuration.revision,self.architecture)


    def generate(self,path):
        """ Ensures that the base system, to create a CHROOT environment, exists """

        # Create all, first, in a temporal folder
        tmp_path = path+".tmp"

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

        if self.distro_number <= 21:
            packages = "fedora-release bash yum util-linux"
        else:
            packages = "fedora-release bash dnf util-linux meson"
        command = "yum -y --config={:s} --releasever={:s} --nogpg --installroot={:s} install {:s}".format(yumcfgpath,self.distro_name,tmp_path,packages)
        if (0 != self.run_external_program(command)):
            shutil.rmtree(tmp_path, ignore_errors=True)
            return True # error!!!

        shutil.rmtree(yumrepospath, ignore_errors=True)
        os.remove(yumcfgpath)

        # for some reason, the RPM database is not complete, so it is a must to reinstall everything from inside the chroot environment
        # umount /sys to avoid failure due to filesystem.rpm. At least with Fedora 21
        if self.distro_number <= 21:
            command = 'bash -c "umount /sys && yum -y --releasever={:s} install {:s}"'.format(self.distro_name,packages)
        else:
            command = 'bash -c "dnf -y --releasever={:s} install {:s}"'.format(self.distro_name,packages)
        if (0 != self.run_chroot(tmp_path, command)):
            shutil.rmtree(tmp_path, ignore_errors=True)
            return True # error!!!

        os.sync()
        os.rename(tmp_path,path) # rename the folder to the definitive name
        os.sync()

        shutil.rmtree(tmp_path, ignore_errors=True)

        return False # no error


    @multipackager_module.package_base.call_with_cache
    def update(self,path):

        """ Ensures that the chroot environment is updated with the lastest packages """

        # Here, we have for sure the CHROOT environment, but maybe it must be updated
        if self.distro_number <= 21:
            command = 'yum update -y'
        else:
            command = 'dnf update -y'
        if (0 != self.run_chroot(path,command)):
            return True # error!!!

        return False


    def read_specs_data(self,working_path):

        if working_path == None:
            return

        self.dependencies = []
        self.dependencies.append("rpm-build")

        if (os.path.exists(os.path.join(working_path,"setup.py"))): # it is a python package
            self.read_python_setup(working_path)
            self.dependencies.append("python3")
            setup_cfg = os.path.join(working_path,"setup.cfg")
            if os.path.exists(setup_cfg):
                pkg_data = configparser.ConfigParser()
                pkg_data.read(setup_cfg)
                if 'bdist_rpm' in pkg_data:
                    if 'build_requires' in pkg_data['bdist_rpm']:
                        deps = pkg_data['bdist_rpm']['build_requires'].split(' ')
                        for dep in deps:
                            dep = dep.strip()
                            if dep == '':
                                continue
                            self.dependencies.append(dep)
                    if 'name' in pkg_data['bdist_rpm']:
                        self.project_name = pkg_data['bdist_rpm']['name']
                    if 'version' in pkg_data['bdist_rpm']:
                        self.project_version = pkg_data['bdist_rpm']['version']
        else:
            self.dependencies.append("meson")
            self.dependencies.append("ninja-build")
            specs_path = self.check_path_in_builds(working_path)
            if (specs_path == None):
                print(_("No rpm folder. Aborting."))
                return True

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
                if line[:9] == "Requires:":
                    self.dependencies.append(line[9:].strip())
                    continue
                if line[:5] == "Name:":
                    self.project_name = line[5:].strip()
                    continue
                if line[:8] == "Version:":
                    self.project_version = line[8:].strip()
                    continue
                if line[:8] == "Release:":
                    continue

    def build_meson(self):

        install_path = os.path.join(self.build_path,"meson")
        if (os.path.exists(install_path)):
            shutil.rmtree(install_path,ignore_errors = True)
        os.makedirs(install_path)

        return self.run_chroot(self.working_path, 'bash -c "cd /project/meson && meson .. && mesonconf -Dprefix=/usr && ninja-build && DESTDIR=/install_root ninja-build install"')


    @multipackager_module.package_base.call_with_cache
    def install_dependencies_full(self,path,deps):

        if self.distro_number <= 21:
            command = "yum -y install"
        else:
            command = "dnf -y install"
        for dep in deps:
            command += " "+dep
        return self.run_chroot(path, command)


    def install_local_package_internal(self, file_name):

        if self.distro_number <= 21:
            command = "yum install -y {:s}".format(file_name)
        else:
            command = "dnf install -y {:s}".format(file_name)

        if 0 != self.run_chroot(self.working_path, command):
            return True
        return False


    def install_dependencies(self,project_path,avoid_packages,preinstall):

        """ Install the dependencies needed for building this package """

        if self.read_specs_data(project_path):
            return True

        deps = []
        for d in self.dependencies:
            if avoid_packages.count(d) == 0:
                deps.append(d)

        if (len(deps) != 0):
            return self.install_dependencies_full(self.base_path,deps)
        return False


    def build_python(self):
        """ Builds a package for a python project """

        destination_dir = os.path.join(self.build_path,"dist")
        shutil.rmtree(destination_dir, ignore_errors = True)

        if (self.run_chroot(self.working_path, 'bash -c "cd /project && python3 setup.py bdist_rpm"')):
            return True

        return False


    def copy_rpms(self,destination_dir):

        files = os.listdir(destination_dir)
        for f in files:
            if f[-11:] == ".noarch.rpm":
                origin_name = os.path.join(destination_dir,f)
                if os.path.isdir(origin_name):
                    if not self.copy_rpms(origin_name):
                        return False
                    continue
                final_name = os.path.join(os.getcwd(),self.get_package_name(self.build_path))
                if (os.path.exists(final_name)):
                    os.remove(final_name)
                shutil.move(origin_name, final_name)
                return False
        return True


    def copy_bin_rpms(self,destination_dir):

        files = os.listdir(destination_dir)
        for f in files:
            origin_name = os.path.join(destination_dir,f)
            if os.path.isdir(origin_name):
                if not self.copy_bin_rpms(origin_name):
                    return False
                continue
            final_name = os.path.join(os.getcwd(),self.get_package_name(self.build_path))
            if (os.path.exists(final_name)):
                os.remove(final_name)
            if f[-4:] == ".rpm":
                shutil.move(origin_name, final_name)
                return False
        return True


    def build_package(self,project_path):
        """ Takes the binaries located at /install_root and build a package """

        setup_python = os.path.join(self.build_path,"setup.py")
        if (os.path.exists(setup_python)):
            destination_dir = os.path.join(self.build_path,"dist")
            return self.copy_rpms(destination_dir)

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

            if line[:8] == "Release:":
                spec_o.write("Release: {:d}\n".format(self.configuration.revision))
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

        return self.copy_bin_rpms(os.path.join(self.working_path,"rpmpackage","RPMS"))
