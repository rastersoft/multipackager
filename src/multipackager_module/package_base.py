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
import re
import functools

def call_with_cache(func):

    @functools.wraps(func)
    def inner(*args):

        self = args[0]
        path = args[1]

        backup_path = path+".backup"

        print(_("Generating a backup for {:s}").format(path))

        if self.copy_cache(path,backup_path):
            return True

        os.sync() # sync disks

        if (func(*args)):
            shutil.rmtree(self.base_path, ignore_errors=True)
            os.rename(backup_path,self.base_path) # rename the backup folder to the original name
            os.sync() # sync disks
            return True # error!

        shutil.rmtree(backup_path, ignore_errors=True)
        os.sync() # sync disks
        return False

    return inner


class package_base(object):

    def __init__(self, configuration, distro_type, distro_name, architecture, cache_name = None):

        self.install_at_lib = False
        self.configuration = configuration
        self.distro_type = distro_type
        self.distro_name = distro_name
        self.architecture = architecture
        self.project_name = "project"
        self.project_version = "1.0"
        self.project_release = "1"
        self.python2 = False
        self.distro_full_name = "{:s} {:s} {:s}".format(distro_type,distro_name,architecture)


        # name of the CHROOT environment to use
        self.base_chroot_name = self.distro_type+"_chroot_"+self.distro_name+"_"+self.architecture
        # path to the origin CHROOT environment to use (the one with only the base system)
        self.base_cache_path = os.path.join(self.configuration.cache_path,self.base_chroot_name)


        if (cache_name != None):
            self.chroot_name = self.base_chroot_name+"_"+cache_name
        else:
            self.chroot_name = self.base_chroot_name

        # path of the base CHROOT enviromnent to use (the one which will be copied to the final one)
        self.base_path = os.path.join(self.configuration.cache_path,self.chroot_name)

        if (self.base_path[-1] == os.path.sep):
            self.base_path = self.base_path[:-1] # remove the last "/" if it exists

        # path of the working copy, where the project has been copied for being build
        self.working_path = None

        # path of the project copy (outside the chroot environment; inside is always "/project")
        self.build_path = None

        # this is the data stored in the setup.py script (if it is a python program)
        self.pysetup = {}


    def install_local_package(self,file_path):
        
        shutil.copy(file_path,self.working_path)
        if self.install_local_package_internal(os.path.join(os.path.sep,os.path.basename(file_path))):
            return True
        print("{:s} instalado bien".format(file_path))
        return False


    def copy_cache(self,origin_path,destination_path, force_delete = True):

        if (os.path.exists(destination_path)) and (force_delete == False):
            return False # don't delete it

        # Create the destination folder and all the previous folders, if needed
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)

        # remove data inside destination path
        shutil.rmtree(destination_path, ignore_errors=True)

        # copy the base system to the path where we want to work with to generate the package
        if (0 != self.run_external_program("cp -a {:s} {:s}".format(origin_path,destination_path))):
            return True # error!!!

        return False


    def add_dns(self,path):

        # Add OpenDNS
        f = open(os.path.join(path,"etc","resolv.conf"),"w")
        f.write("# OpenDNS IPv4 nameservers\nnameserver 208.67.222.222\nnameserver 208.67.220.220\n# OpenDNS IPv6 nameservers\nnameserver 2620:0:ccc::2\nnameserver 2620:0:ccd::2\n")
        f.close()


    def check_environment(self):

        """ Ensures that both caches (the base_cache_path, for shells, containing the bare minimum system, and the base_path
            with an updated system) exists """

        if not os.path.exists(self.base_cache_path):
            print(_("Generating the environment for {:s}").format(self.base_chroot_name))
            if self.generate(self.base_cache_path):
                print(_("Failed to initializate environment for {:s}").format(self.base_chroot_name))
                return True # error!!!
            self.add_dns(self.base_cache_path)

        if not os.path.exists(self.base_path):
            if self.copy_cache(self.base_cache_path,self.base_path):
                print(_("Failed to initializate environment for {:s}").format(self.base_chroot_name))
                return True # error!!!

        return False


    def install_postdependencies(self,project_path):
        return False


    def prepare_working_path(self,final_path = None):

        """ Creates a working copy of the chroot environment to keep the original untouched.
            If final_path is None, will copy the compilation cache (base_path) to a working path; if not,
            will copy the bare minimum cache for shells (base_cache_path) to that path """

        if final_path == None:
            self.working_path = os.path.join(self.configuration.working_path,self.base_chroot_name)
            original_path = self.base_path
        else:
            self.working_path = final_path
            original_path = self.base_cache_path

        shutil.rmtree(self.working_path, ignore_errors=True)
        if (0 != self.run_external_program("cp -a {:s} {:s}".format(original_path,self.working_path))): # copy the base system to the path where we want to work with to generate the package
            print(_("Failed to create the working environment at {:s} from {:s}").format(self.working_path,original_path))
            return True # error!!!

        # environment ready
        return False


    def update_environment(self):

        """ Ensures that the environment is updated with the last packages """

        print(_("Updating {:s}").format(self.base_chroot_name))
        self.update(self.base_cache_path)
        return self.update(self.base_path)


    def clear_cache(self):

        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path, ignore_errors = True)

        if os.path.exists(self.base_cache_path):
            shutil.rmtree(self.base_cache_path, ignore_errors = True)


    def build_project(self,project_path):

        """ Builds the specified project inside the working copy of the chroot environment """

        self.build_path = os.path.join(self.working_path,"project")

        os.makedirs(self.build_path)

        # copy the project folder inside the CHROOT environment, in the "/project" folder

        if (0 != self.run_external_program("cp -a {:s} {:s}".format(os.path.join(project_path,"*"),os.path.join(self.working_path,"project/")))):
            return True # error!!!

        # the compiled binaries will be installed in /install_root, inside the chroot environment
        install_path = os.path.join(self.working_path,"install_root")
        shutil.rmtree(install_path, ignore_errors = True)
        os.makedirs (install_path)

        specific_creator = "multipackager_{:s}.sh".format(self.distro_type)
        # check the install system available
            # First, check if exists a shell file called 'multipackager_DISTROTYPE.sh' (like multipackager_debian.sh, or multipackager_ubuntu.sh)
        if (os.path.exists(os.path.join(self.build_path,specific_creator))):
            if self.build_multipackager(specific_creator):
                return True
            # Now check if it exists a generic shell script called 'multipackager.sh'
        elif (os.path.exists(os.path.join(self.build_path,"multipackager.sh"))):
            if self.build_multipackager("multipackager.sh"):
                return True
            # Check if it is a python program
        elif (os.path.exists(os.path.join(self.build_path,"setup.py"))):
            if self.build_python():
                return True
            # Check if it is an autoconf/automake with the 'configure' file already generated
        elif (os.path.exists(os.path.join(self.build_path,"configure"))):
            if self.build_autoconf(False):
                return True
            # Now check if it is an autoconf/automake without the 'configure' file generated
        elif (os.path.exists(os.path.join(self.build_path,"autogen.sh"))):
            if self.build_autoconf(True):
                return True
            # Check if it is a CMake project
        elif (os.path.exists(os.path.join(self.build_path,"CMakeLists.txt"))):
            if self.build_cmake():
                return True
            # Finally, try with a classic Makefile
        elif (os.path.exists(os.path.join(self.build_path,"Makefile"))):
            if self.build_makefile():
                return True
        else:
            print (_("Unknown build system"))
            return True

        self.copy_perms(self.working_path,install_path)
        return False


    def build_multipackager(self,filename):

        return self.run_chroot(self.working_path, 'bash -c "cd /project && source {:s} /install_root"'.format(filename))


    def build_cmake(self):

        install_path = os.path.join(self.build_path,"install")
        if (os.path.exists(install_path)):
            shutil.rmtree(install_path,ignore_errors = True)
        os.makedirs(install_path)

        if self.install_at_lib:
            return self.run_chroot(self.working_path, 'bash -c "cd /project/install && cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=/usr/lib && make && make DESTDIR=/install_root install"')
        else:
            return self.run_chroot(self.working_path, 'bash -c "cd /project/install && cmake .. -DCMAKE_INSTALL_PREFIX=/usr && make && make DESTDIR=/install_root install"')


    def build_autoconf(self,autogen):

        if (autogen):
            if (self.run_chroot(self.working_path, 'bash -c "cd /project && ./autogen.sh"')):
                return True

        return self.run_chroot(self.working_path, 'bash -c "cd /project && ./configure --prefix=/usr && make clean && make && make DESTDIR=/install_root install"')


    def build_makefile(self):

        return self.run_chroot(self.working_path, 'bash -c "cd /project && make clean && make && make PREFIX=/usr DESTDIR=/install_root install"')


    def get_string(self,line):
        gen_string = re.compile("[\"'][^\"']+[\"']")
        p = gen_string.match(line)
        if p != None:
            return p.group()[1:-1]
        else:
            return None


    def read_python_setup(self,working_path):

        final_path = os.path.join(working_path,"setup.py")
        if not os.path.exists(final_path):
            return

        params = [ 'name', 'version', 'author', 'author-email', 'maintainer', 'maintainer-email','url','license','description','long-description','keywords' ]
        for param in params:
            prc = subprocess.Popen( [final_path , '--'+param], cwd=working_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            sout,serr = prc.communicate()
            data = sout.decode().strip()
            self.pysetup[param] = data
            if param == 'name' and data != '':
                self.project_name = data
            elif param == 'version' and data != '':
                self.project_version = data


    def cleanup(self):

        if self.working_path != None:
            shutil.rmtree(self.working_path)
        return False


    def run_external_program(self,command):

        print(_("Launching {:s}").format(str(command)))
        proc = subprocess.Popen(command, shell=True)
        return (proc.wait() != 0)


    def run_chroot(self,base_path,command,username = None):

        if self.architecture == "i386":
            personality = "x86"
        else:
            personality = "x86-64"

        if username != None:
            userparam = "--user={:s}".format(username)
        else:
            userparam = ""

        command = "systemd-nspawn {:s} -D {:s} --personality {:s} {:s}".format(userparam,base_path,personality,command)
        return self.run_external_program(command)


    def set_perms(self,filename):

        if (os.path.exists(filename)):
            os.chmod(filename, 0o755)


    def copy_perms(self,template,final_folder):

        files = os.listdir(final_folder)
        for file in files:
            template_file = os.path.join(template,file)
            if not os.path.exists(template_file):
                continue
            if not os.path.isdir(template_file):
                continue
            final_file = os.path.join(final_folder,file)
            statinfo = os.stat(template_file,follow_symlinks=False)
            os.chmod(final_file, statinfo.st_mode)
            os.chown(final_file, statinfo.st_uid, statinfo.st_gid, follow_symlinks=False)
            if os.path.isdir(final_file):
                self.copy_perms(template_file, final_file)