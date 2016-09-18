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

class debian (multipackager_module.package_base.package_base):

    def __init__(self, configuration, distro_type, distro_name, architecture, cache_name = None):

        multipackager_module.package_base.package_base.__init__(self, configuration, distro_type, distro_name, architecture, cache_name)


    def check_path_in_builds(self,project_path):

        if self.distro_type == "ubuntu":
            # Try the "ubuntu" folder, and if it doesn't exists, try with "debian" one
            if self.architecture == "i386":
                path_list = ["ubuntu32","UBUNTU32","Ubuntu32","ubuntu","UBUNTU","Ubuntu","debian32","DEBIAN32","Debian32","debian","DEBIAN","Debian"]
            else:
                path_list = ["ubuntu64","UBUNTU64","Ubuntu64","ubuntu","UBUNTU","Ubuntu","debian64","DEBIAN64","Debian64","debian","DEBIAN","Debian"]
        else:
            if self.architecture == "i386":
                path_list = ["debian32","DEBIAN32","Debian32","debian","DEBIAN","Debian"]
            else:
                path_list = ["debian64","DEBIAN64","Debian64","debian","DEBIAN","Debian"]

        for element in path_list:
            path = os.path.join(project_path,element)
            if os.path.exists(path):
                return path
        return None


    def set_project_version(self,text):

        pos = text.rfind("-")
        if (pos != -1):
            text = text[:pos]
        self.project_version = text


    def get_package_name(self,project_path):
        """ Returns the final package name for the project specified, or None if can't be determined yet """

        if (os.path.exists(os.path.join(project_path,"setup.py"))):
            self.read_python_setup(project_path)
            package_name = "{:s}-{:s}-{:s}_{:s}-{:s}{:d}_all.deb".format("python2" if self.python2 else "python3",self.project_name,self.distro_name,self.project_version,self.distro_type,self.configuration.revision)
        else:
            debian_path = self.check_path_in_builds(project_path)
            if (debian_path == None):
                return True

            control_path = os.path.join(debian_path,"control")
            if (not os.path.exists(control_path)):
                return True

            f = open (control_path,"r")
            for line in f:
                if line[:7] == "Source:":
                    self.project_name = line[7:].strip()
                    continue
                if line[:8] == "Package:":
                    self.project_name = line[8:].strip()
                    continue
                if line[:8] == "Version:":
                    self.set_project_version(line[8:].strip())
                    continue
            f.close()
            package_name = "{:s}-{:s}_{:s}-{:s}{:d}_{:s}.deb".format(self.project_name,self.distro_name,self.project_version,self.distro_type,self.configuration.revision,self.architecture)
        return package_name


    def generate(self,path):
        """ Ensures that the base system, to create a CHROOT environment, exists """

        # Create all, first, in a temporal folder
        tmp_path = path+".tmp"

        shutil.rmtree(tmp_path, ignore_errors=True)

        os.makedirs(tmp_path)
        if self.distro_type == "debian":
            server = "http://http.debian.net/debian/"
        else:
            server = "http://archive.ubuntu.com/ubuntu/"
        command = "debootstrap --variant=buildd --arch {:s} {:s} {:s} {:s}".format(self.architecture,self.distro_name,tmp_path,server)


        if (0 != self.run_external_program(command)):
            return True # error!!!

        f = open(os.path.join(tmp_path,"etc","apt","sources.list"),"w")
        if (self.distro_type == "debian"):
            # Add contrib and non-free to the list of packages sources if DEBIAN
            f.write("deb http://ftp.debian.org/debian/ {:s} main contrib non-free\n".format(self.distro_name))
        else:
            # Add restricted, universe and multiverse if UBUNTU
            f.write("deb http://archive.ubuntu.com/ubuntu/ {:s} main restricted universe multiverse\n".format(self.distro_name))
        f.close()

        command = 'apt-get update'
        if (0 != self.run_chroot(tmp_path,command)):
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

        retval = self.run_chroot(path,"apt-get update")
        if (retval != 0):
            return True # error!!!!

        retval = self.run_chroot(path,"apt-get dist-upgrade -y")
        if (retval != 0):
            return True # error!!!!

        return False


    @multipackager_module.package_base.call_with_cache
    def install_dependencies_full(self,path,dependencies):

        command = "apt-get install -y"
        for dep in dependencies:
            command += " "+dep
        return self.run_chroot(path, command)


    def install_local_package_internal(self, file_name):
        
        if 0 != self.run_chroot(self.working_path, "dpkg -i {:s}".format(file_name)):
            if 0 != self.run_chroot(self.working_path, "apt-get install -f -y"):
                return True
        return False


    def install_dependencies(self,project_path,avoid_packages,preinstall):

        """ Install the dependencies needed for building this package """

        dependencies = []

        if (os.path.exists(os.path.join(project_path,"setup.py"))): # it is a python package
            control_path = os.path.join(project_path,"stdeb.cfg")
            dependencies.append("python3")
            dependencies.append("python3-stdeb")
            dependencies.append("python3-all")
            dependencies.append("python-all")
            dependencies.append("fakeroot")
        else:
            debian_path = self.check_path_in_builds(project_path)
            if debian_path == None:
                print (_("There is no DEBIAN/UBUNTU folder with the package specific data"))
                return True

            control_path = os.path.join(debian_path,"control")
            if (not os.path.exists(control_path)):
                print (_("There is no CONTROL file with the package specific data"))
                return True

        f = open (control_path,"r")
        for line in f:
            if (line[:7] == "Depends") or (line[:13] == "Build-Depends"):
                if (line[:7] == "Depends"):
                    tmp = line[7:].strip()
                else:
                    tmp = line[13:].strip()
                if (tmp[0] == ':') or (tmp[0] == '='):
                    tmp = tmp[1:].strip()
                tmp = tmp.split(",")
                for element2 in tmp:
                    tmp2 = element2.split("|")
                    # if it is a single package, just add it as-is
                    if (len(tmp2) == 1):
                        dependencies.append(element2.strip())
                        continue
                    # but if there are several optional packages, check each one and install the first found
                    list_p = ""
                    found = False
                    for element in tmp2:
                        pos = element.find("(") # remove version info
                        if (pos != -1):
                            element = element[:pos]
                        list_p += " "+element
                        command = "apt-cache show {:s}".format(element)
                        if (0 == self.run_chroot(self.base_path, command)):
                            dependencies.append(element.strip())
                            found = True
                            break
                    if not found:
                        print (_("Cant find any of these packages in the guest system:{:s}").format(list_p))
                        return True
                continue
            if line[:7] == "Source:":
                self.project_name = line[7:].strip()
                continue
            if line[:8] == "Package:":
                self.project_name = line[8:].strip()
                continue
            if line[:8] == "Version:":
                self.set_project_version(line[8:].strip())
                continue
        f.close()

        if (len(dependencies) != 0):
            deps2 = []
            for d in dependencies:
                if avoid_packages.count(d) == 0:
                    deps2.append(d)
            return self.install_dependencies_full(self.base_path,deps2)
        return False


    def build_python(self):
        """ Builds a package for a python project """

        destination_dir = os.path.join(self.build_path,"deb_dist")
        shutil.rmtree(destination_dir, ignore_errors = True)

        if (self.run_chroot(self.working_path, 'bash -c "cd /project && python3 setup.py --command-packages=stdeb.command bdist_deb"')):
            return True
        return False


    def copy_pacs(self,destination_dir,package_name):

        files = os.listdir(destination_dir)
        for f in files:
            if f[-4:] == ".deb":
                origin_name = os.path.join(destination_dir,f)
                final_name = os.path.join(os.getcwd(),package_name)
                if (os.path.exists(final_name)):
                    os.remove(final_name)
                if os.path.isdir(origin_name):
                    if not self.copy_pacs(origin_name,package_name):
                        return False
                shutil.move(origin_name, final_name)
                return False
        return True


    def build_package(self,project_path):
        """ Takes the binaries located at /install_root and build a package """

        setup_python = os.path.join(self.build_path,"setup.py")
        if (os.path.exists(setup_python)):
            destination_dir = os.path.join(self.build_path,"deb_dist")
            package_name = self.get_package_name(self.build_path)
            return self.copy_pacs(destination_dir,package_name)

        debian_path = self.check_path_in_builds(project_path)

        package_path = os.path.join(self.working_path,"install_root","DEBIAN")
        os.makedirs(package_path)
        command = "cp -a {:s} {:s}".format(os.path.join(debian_path,"*"),package_path)
        if 0 != self.run_external_program(command):
            return True

        self.set_perms(os.path.join(package_path,"preinst"))
        self.set_perms(os.path.join(package_path,"postinst"))
        self.set_perms(os.path.join(package_path,"prerm"))
        self.set_perms(os.path.join(package_path,"postrm"))

        control_path = os.path.join(package_path,"control")
        f1 = open (control_path,"r")
        f2 = open (control_path+".tmp","w")
        for line in f1:
            line = line.replace("\n","").replace("\r","")
            if (line == ""): # remove blank lines, just in case
                continue
            elif (line[:13] == "Architecture:"):
                arch = line[13:].strip()
                if (arch == "any"):
                    line = "Architecture: {:s}".format(self.architecture)
            elif (line[:7] == "Source:"):
                continue
            elif (line[:14] == "Build-Depends:"):
                continue
            elif (line[:8] == "Version:"):
                line = "Version: {:s}".format(self.project_version)
                f2.write("Installed-Size: {:d}\n".format(int(self.program_size/1024)))
            elif (line[:15] == "Installed-Size:"):
                continue
            f2.write(line+"\n")
        f1.close()
        f2.close()
        os.remove(control_path)
        os.rename(control_path+".tmp",control_path)
        package_name = self.get_package_name(self.build_path)
        command = 'bash -c "cd / && dpkg -b /install_root {:s}"'.format(package_name)
        if (self.run_chroot(self.working_path, command)):
            return True
        shutil.move(os.path.join(self.working_path,package_name), os.getcwd())
        return False
