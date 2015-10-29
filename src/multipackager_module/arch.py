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

class arch (multipackager_module.package_base.package_base):

    def __init__(self, configuration, distro_type, distro_name, architecture, cache_name = None):

        multipackager_module.package_base.package_base.__init__(self, configuration, distro_type, distro_name, architecture, cache_name)
        self.install_at_lib = True


    def set_project_version(self,text):

        pos = text.rfind("-")
        if (pos != -1):
            text = text[:pos]
        self.project_version = text


    def get_package_name(self,project_path):
        """ Returns the final package name for the project specified, or None if can't be determined yet """

        if (os.path.exists(os.path.join(project_path,"setup.py"))):
            self.read_python_setup(project_path)
            package_name = "{:s}-{:s}-{:s}-{:d}-any.pkg.tar.xz".format("python2" if self.python2 else "python",self.project_name,self.project_version,self.configuration.revision)
        else:
            pacman_path = os.path.join(project_path,"PKGBUILD")
            if (not os.path.exists(pacman_path)):
                return True

            f = open (pacman_path,"r")
            for line in f:
                if line[:8] == "pkgname=":
                    self.project_name = line[8:].strip()
                    continue
                if line[:7] == "pkgver=":
                    self.set_project_version(line[7:].strip())
                    continue
            f.close()
            package_name = "{:s}-{:s}-{:d}-{:s}.pkg.tar.xz".format(self.project_name,self.project_version,self.configuration.revision,"i686" if self.architecture=="i386" else "x86_64")
        return package_name


    def generate(self,path):
        """ Ensures that the base system, to create a CHROOT environment, exists """

        # Create all, first, in a temporal folder
        tmp_path = path+".tmp"

        shutil.rmtree(tmp_path, ignore_errors=True)

        os.makedirs(tmp_path)
        server = self.configuration.arch_mirror

        if (server[-1] == '/'):
            server = server[:-1]

        filename = "archlinux-bootstrap-{:s}-{:s}.tar.gz".format(self.distro_name,"i686" if self.architecture=="i386" else "x86_64")
        output_filename = os.path.join(self.configuration.cache_path,filename)

        try:
            os.remove(output_filename)
        except:
            pass

        command = "wget {:s}/iso/{:s}/{:s} -O {:s}".format(server,self.distro_name,filename,output_filename)

        if (0 != self.run_external_program(command)):
            return True # error!!!

        final_filename = os.path.join(self.configuration.cache_path , "root." + ("i686" if self.architecture == "i386" else "x86_64"))
        shutil.rmtree(final_filename, ignore_errors=True)

        command = 'bash -c "cd {:s} && tar xf {:s}"'.format(self.configuration.cache_path,filename)
        if (0 != self.run_external_program(command)):
            return True # error!!!

        try:
            os.remove(output_filename)
        except:
            pass

        os.rename(final_filename,tmp_path)

        mirrors = open(os.path.join(tmp_path,"etc","pacman.d","mirrorlist"),"w")
        mirrors.write("Server = {:s}/$repo/os/$arch\n".format(server))
        mirrors.close()

        command = "pacman-key --init"
        if (0 != self.run_chroot(tmp_path,command)):
            return True # error!!!

        command = "pacman-key --populate archlinux"
        if (0 != self.run_chroot(tmp_path,command)):
            return True # error!!!

        command = "pacman -r / -Syu --noconfirm base"
        if (0 != self.run_chroot(tmp_path,command)):
            return True # error!!!

        command = "useradd multipackager -m -b /"
        if (0 != self.run_chroot(tmp_path,command)):
            return True # error!!!

        command = "pacman -S --noconfirm fakeroot make gcc patch cmake autoconf automake"
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

        retval = self.run_chroot(path,"pacman -Syu --noconfirm")
        if (retval != 0):
            return True # error!!!!

        return False


    @multipackager_module.package_base.call_with_cache
    def install_dependencies_full(self,path,dependencies):

        command = "pacman --noconfirm -S"
        for dep in dependencies:
            command += " "+dep
        return self.run_chroot(path, command)


    def read_deps(self,pacman_path,read_extra_data):

        dependencies = []

        f = open (pacman_path,"r")
        multiline = False
        full_line = ""
        for line in f:
            if multiline:
                full_line += line
                if (full_line.find(")") != -1):
                    multiline = False
                else:
                    continue
            else:
                full_line = line

            tmp = None

            if (full_line[:12] == "makedepends=") or (full_line[:12] == "makedepend =") :
                if (full_line.find(")") == -1) and (full_line.find("(") != -1):
                    multiline = True
                    continue
                tmp = full_line[12:].replace("(","").replace(")","").replace("'","").replace('"',"").strip().split(" ")
            elif (line[:8] == "depends=") or (line[:8] == "depend ="):
                if (full_line.find(")") == -1) and (full_line.find("(") != -1):
                    multiline = True
                    continue
                tmp = full_line[8:].replace("(","").replace(")","").replace("'","").replace('"',"").strip().split(" ")
            elif read_extra_data:
                if full_line[:8] == "pkgname=":
                    self.project_name = line[8:].strip()
                elif full_line[:7] == "pkgver=":
                    self.set_project_version(line[7:].strip())
                continue

            if tmp == None:
                continue
            for element in tmp:
                pos = element.find(">")
                if pos != -1:
                    element = element[:pos]
                pos = element.find("<")
                if pos != -1:
                    element = element[:pos]
                pos = element.find("=")
                if pos != -1:
                    element = element[:pos]
                if (element != "") and (dependencies.count(element) == 0):
                    dependencies.append(element)
        f.close()
        return dependencies


    def check_dependencies(self,tmp_path,dependencies,main_dependencies,aur_dependencies):

        new_dependencies = []

        for dep in dependencies:
            if (dep == "sh"):
                dep = "bash"
            command = "pacman -Q {:s}".format(dep)
            if not self.run_chroot(self.base_path, command):
                continue # this package is already installed
            command = "pacman -Si {:s}".format(dep)
            if not self.run_chroot(self.base_path, command):
                if main_dependencies.count(dep) == 0:
                    main_dependencies.append(dep) # the package is available in the oficial repository
            else:
                package_dir = os.path.join(tmp_path,dep)
                pkgbuild_path = os.path.join(tmp_path,"{:s}.tar.gz".format(dep))
                command = "wget https://aur.archlinux.org/packages/{:s}/{:s}/{:s}.tar.gz -O {:s}".format(dep[:2],dep,dep,pkgbuild_path)
                if 0 != self.run_external_program(command):
                    command = "wget https://aur.archlinux.org/cgit/aur.git/snapshot/{:s}.tar.gz -O {:s}".format(dep,pkgbuild_path)
                    if 0 != self.run_external_program(command):
                        if dep[:7] != 'python2':
                            print(_("The package {:s} is not available in the official repositories, neither in the AUR repositories.").format(dep))
                            return None
                        # If it is a python2 package, and doesn't exists, try without the "2"
                        dep2 = 'python'+dep[7:]
                        pkgbuild_path = os.path.join(tmp_path,"{:s}.tar.gz".format(dep2))
                        package_dir = os.path.join(tmp_path,dep2)
                        command = "wget https://aur.archlinux.org/packages/{:s}/{:s}/{:s}.tar.gz -O {:s}".format(dep[:2],dep2,dep2,pkgbuild_path)
                        if 0 != self.run_external_program(command):
                            command = "wget https://aur.archlinux.org/cgit/aur.git/snapshot/{:s}.tar.gz -O {:s}".format(dep2,pkgbuild_path)
                            if 0 != self.run_external_program(command):
                                print(_("The package {:s} is not available in the official repositories, neither in the AUR repositories.").format(dep))
                                return None
                        dep = dep2
                command = 'bash -c "cd {:s} && tar xf {:s}.tar.gz"'.format(tmp_path,dep)
                if 0 != self.run_external_program(command):
                    print(_("The package {:s} could not be uncompressed.").format(dep))
                    return None
                pkgbuild_path = os.path.join(package_dir,"PKGBUILD")
                aur_dependencies.insert(0,dep) # the package is available in the AUR repository
                tmpdeps = self.read_deps(pkgbuild_path, False)
                for dep2 in tmpdeps:
                    if (0 != aur_dependencies.count(dep2)):
                        aur_dependencies.remove(dep2)
                        aur_dependencies.insert(0,dep2) # move it to the start
                    elif (0 != dependencies.count(dep2)):
                        continue # will be checked in this loop, so there is no need of pass it again to the next loop
                    elif (0 == main_dependencies.count(dep2)) and (0 == new_dependencies.count(dep2)):
                        new_dependencies.append(dep2)

        return new_dependencies


    def install_packages(self,package_list):

        main_dependencies = []
        self.aur_dependencies = []

        tmp_path = os.path.join(self.base_path,"built_tmp_packages")
        shutil.rmtree(tmp_path, ignore_errors=True)
        os.makedirs(tmp_path)

        while (len(package_list) != 0):
            package_list = self.check_dependencies(tmp_path, package_list, main_dependencies, self.aur_dependencies)
            if package_list == None:
                return True

        # Install first the dependencies from the main repository
        if (len(main_dependencies) != 0):
            if self.install_dependencies_full(self.base_path,main_dependencies):
                return True

        return False


    def build_AUR_package(self,path):

        fullpath = os.path.join(self.working_path,path)
        pkgfullpath = os.path.join(fullpath,"PKGBUILD")

        if not os.path.exists(pkgfullpath):
            return False

        os.chmod(fullpath, 511) # 777 permissions


        command = 'bash -c "mkdir -p ~/.gnupg && echo -e \\"keyserver hkp://keys.gnupg.net\nkeyserver-options auto-key-retrieve\\" > ~/.gnupg/gpg.conf && cd {:s} && makepkg"'.format(path)
        if self.run_chroot(self.working_path, command, "multipackager"):
            return True

        for file in os.listdir(fullpath):
            if (file[-11:]==".pkg.tar.xz"):
                command = 'pacman --noconfirm -U {:s}'.format(os.path.join(path,file))
                return self.run_chroot(self.working_path, command)
        print(_("Unable to install the created package for {:s}").format(path))
        return True


    def install_postdependencies(self,project_path):

        print("Aur: "+str(self.aur_dependencies))
        tmp_path = os.path.join(self.working_path,"built_tmp_packages")
        for paths in self.aur_dependencies:
            full_path = os.path.join("built_tmp_packages",paths)
            if self.build_AUR_package(full_path):
                print (_("Failed to build package {:s}. Aborting").format(paths))
                return True
        return False


    def read_deps_python(self,path,sep = False):

        if not os.path.exists(path):
            return []
        
        dependencies = []
        makedepends = []
        pkg_data = configparser.ConfigParser()
        pkg_data.read(path)
        if 'depends' in pkg_data['DEFAULT']:
            deps = pkg_data['DEFAULT']['depends'].split(',')
            for dep in deps:
                dependencies.append(dep.strip())
        if 'makedepends' in pkg_data['DEFAULT']:
            deps = pkg_data['DEFAULT']['makedepends'].split(',')
            for dep in deps:
                if sep:
                    makedepends.append(dep.strip())
                else:
                    dependencies.append(dep.strip())

        if sep:
            return dependencies,makedepends
        else:
            return dependencies


    def install_local_package_internal(self, file_name):

        if 0 != self.run_chroot(self.working_path, "pacman --noconfirm -U {:s}".format(file_name)):
            return True
        return False


    def install_dependencies(self,project_path,avoid_packages,preinstall):

        """ Install the dependencies needed for building this package """

        dependencies = []

        if (os.path.exists(os.path.join(project_path,"setup.py"))): # it is a python package
            pacman_path = os.path.join(project_path,"stpacman.cfg")
            dependencies = self.read_deps_python(pacman_path)
            dependencies.append("python")
            dependencies.append("python2")
        else:
            pacman_path = os.path.join(project_path,"PKGBUILD")
            if (not os.path.exists(pacman_path)):
                print (_("There is no PKGBUILD file with the package specific data"))
                return True
            dependencies = self.read_deps(pacman_path,True)

        if self.distro_full_name in preinstall:
            tmp_path = "/var/tmp/multipackager_arch_tmp"
            pkg_path = os.path.join(tmp_path,".PKGINFO")
            for f in preinstall[self.distro_full_name]:
                if os.path.exists(tmp_path):
                    shutil.rmtree(tmp_path, ignore_errors = True)
                os.makedirs(tmp_path)
                if 0 != self.run_external_program("tar -xf {:s} -C {:s}".format(f,tmp_path)):
                    return True
                if os.path.exists(pkg_path):
                    dp = self.read_deps(pkg_path,False)
                    for d in dp:
                        dependencies.append(d)
                
        deps = []
        for dep in dependencies:
            if avoid_packages.count(dep) == 0:
                deps.append(dep)

        return self.install_packages(deps)


    def build_python(self):
        """ Builds a package for a python project """

        return False


    def copy_pacs(self,destination_dir,package_name):

        files = os.listdir(destination_dir)
        for f in files:
            if f[-7:] == ".tar.xz":
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

        build_path = os.path.join(self.build_path,"build")
        shutil.rmtree(build_path, ignore_errors=True)

        print("\n\n\nCreating "+build_path+"\n\n\n")
        setup_python = os.path.join(self.build_path,"setup.py")
        if (os.path.exists(setup_python)):
            is_python = True
        else:
            is_python = False

        pkgbuild = os.path.join(self.build_path,"PKGBUILD")

        if os.path.exists(pkgbuild):
            do_copy = True
            pkg_copy = os.path.join(self.build_path,"PKGBUILD_copy")
            os.rename(pkgbuild,pkg_copy)

            f1 = open(pkg_copy,"r")
            f2 = open(pkgbuild,"w")

            for line in f1:
                if (line[:8]=="pkgver()") or (line[:9]=="prepare()") or (line[:7]=="build()") or (line[:7]=="check()") or (line[:9]=="package()"):
                    break
                f2.write(line)
        else:
            do_copy = False
            f2 = open(pkgbuild,"w")
            f2.write("pkgname={:s}\n".format(self.pysetup["name"]))
            f2.write("pkgver={:s}\n".format(self.pysetup["version"]))
            f2.write("pkgrel={:s}\n".format(self.project_release))
            f2.write('pkgdesc="{:s}"\n'.format(self.pysetup["long-description"]))
            if (self.pysetup["url"] != "UNKNOWN"):
                f2.write('url={:s}\n'.format(self.pysetup["url"]))
            if (self.pysetup["license"] != "UNKNOWN"):
                f2.write('license={:s}\n'.format(self.pysetup["license"]))
            f2.write("arch=( 'any' )\n")
            pacman_path = os.path.join(project_path,"stpacman.cfg")
            if os.path.exists(pacman_path):
                deps, makedeps = self.read_deps_python(pacman_path, True)
                f2.write("depends=( ")
                py3 = False
                for d in deps:
                    f2.write("'{:s}' ".format(d))
                    if d == "python":
                        py3 = True
                if not py3:
                    f2.write("'python' ")
                f2.write(")\nmakedepends=( ")
                py3 = False
                for d in makedeps:
                    f2.write("'{:s}' ".format(d))
                    if d == "python":
                        py3 = True
                if not py3:
                    f2.write("'python' ")
                f2.write(")\n")
            else:
                f2.write("depends=( )\nmakedepends=( )\n")

        f2.write("\nbuild() {\n")
        f2.write("\techo Fake build\n")
        f2.write("}\n\n")
        f2.write("package() {\n")
        f2.write("\trm -rf ${pkgdir}\n")
        f2.write("\tmkdir -p ${pkgdir}\n")
        if is_python:
            f2.write("\tcd /project\n")
            f2.write("\tpython3 setup.py install --prefix /usr --root ${pkgdir}\n")
        else:
            f2.write("\tcp -a /install_root/* ${pkgdir}\n")
        f2.write("}\n")
        
        if do_copy:
            f1.close()
        f2.close()


        os.chmod(self.build_path, 511) # 777 permissions

        command = 'bash -c "cd /project && makepkg"'
        if self.run_chroot(self.working_path, command, "multipackager"):
            return True

#         if is_python:
#             destination_dir = os.path.join(self.working_path,"arch_dist")
#             package_name = self.get_package_name(self.build_path)
#             return self.copy_pacs(destination_dir,package_name)

        for file in os.listdir(self.build_path):
            if (file[-11:]==".pkg.tar.xz"):
                shutil.move(os.path.join(self.build_path,file), os.path.join(os.getcwd(),self.get_package_name(project_path)))
                return False
        print(_("Unable to move the created package"))
        return True
