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
import stat

def call_with_cache(func):

    @functools.wraps(func)
    def inner(*args):

        self = args[0]
        path = args[1]

        overlay_path = path+".empty"
        mount_path = path+".mount"
        work_path = path+".work"

        print(_("Sanitary umount, to ensure that there aren't old mounting points"))

        self.run_external_program("umount {:s}".format(mount_path))
        print(_("Mounting overlayfs for {:s} at {:s}, using {:s} for new files").format(path,mount_path,overlay_path))

        # remove data inside destination path
        shutil.rmtree(overlay_path, ignore_errors=True)
        shutil.rmtree(mount_path, ignore_errors=True)
        shutil.rmtree(work_path, ignore_errors=True)
        try:
            os.mkdir(overlay_path)
        except:
            pass
        try:
            os.mkdir(mount_path)
        except:
            pass
        try:
            os.mkdir(work_path)
        except:
            pass

        if (0 != self.run_external_program('mount -t overlay -o rw,lowerdir="{:s}",upperdir="{:s}",workdir="{:s}" overlay "{:s}"'.format(path,overlay_path,work_path,mount_path))):
            return True # error!!!

        args2 = []
        for a in range(len(args)):
            if a == 1:
                args2.append(mount_path)
            else:
                args2.append(args[a])

        try:
            retval = func(*args2)
        except:
            retval = true

        self.run_external_program("umount {:s}".format(mount_path))
        if (not retval):
            print(_("Mixing file systems"))
            self.merge_overlay(path,overlay_path)

        shutil.rmtree(overlay_path, ignore_errors=True)
        shutil.rmtree(mount_path, ignore_errors=True)
        shutil.rmtree(work_path, ignore_errors=True)
        os.sync() # sync disks

        return retval

    return inner


class package_base(object):

    def full_delete(self,path):

        if os.path.exists(path) is False:
            return

        status = os.lstat(path)
        if stat.S_ISDIR(status.st_mode) is True:
            shutil.rmtree(path)
        else:
            os.remove(path)


    def merge_overlay(self,path,overlay_path):

        for f in os.listdir(overlay_path):
            original_file = os.path.join(path,f)
            final_file = os.path.join(overlay_path,f)
            status = os.lstat(final_file)

            # if it is a character device with 0 as major number, the original file/folder must be deleted
            if (stat.S_ISCHR(status.st_mode) is True) and (os.major(status.st_rdev) == 0):
                self.full_delete(original_file)
                continue

            # if it is a newly created file or folder, we just move it. That way it is faster and everything is preserved
            if os.path.exists(original_file) is False:
                self.run_external_program('mv "{:s}" "{:s}"'.format(final_file,original_file), False)
                continue

            ostatus = os.lstat(original_file)
            # if it is a file, just copy it and overwrite
            if (stat.S_ISDIR(status.st_mode) is False):
                self.full_delete(original_file)
                self.run_external_program('cp -a "{:s}" "{:s}"'.format(final_file,original_file), False)
                continue

            # if the new element is a folder, but the old is a file, delete the file and move the folder
            if (stat.S_ISDIR(ostatus.st_mode) is False):
                self.full_delete(original_file)
                self.run_external_program('mv "{:s}" "{:s}"'.format(final_file,original_file), False)
                continue

            # if we reach here, both elements are folders, so let's check them recursively
            shutil.copystat(final_file,original_file) # set permission bits
            if (status.st_uid != ostatus.st_uid) or (status.st_gid != ostatus.st_gid):
                shutil.chown(original_file,status.st_uid,status.st_gid)
            self.merge_overlay(original_file,final_file)


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
        self.program_size = 0

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

        self.used_overlay = False
        self.upper_path = None
        self.overlay_path = None


    def cleanup(self):

        if self.working_path != None:
            shutil.rmtree(self.working_path, ignore_errors=True)
            if self.used_overlay:
                self.run_external_program('umount "{:s}"'.format(self.working_path))
                self.used_overlay = False
        if self.upper_path != None:
            shutil.rmtree(self.upper_path, ignore_errors=True)
            self.upper_path = None
        if self.overlay_path != None:
            shutil.rmtree(self.overlay_path, ignore_errors=True)
            self.overlay_path = None

        return False

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


    def prepare_working_path_overlay(self):

        """ Creates an overlay of the chroot environment to keep the original untouched. """

        self.working_path = os.path.join(self.configuration.working_path,self.base_chroot_name)
        self.upper_path = self.working_path+".upper"
        self.overlay_path = self.working_path+".overlay"
        original_path = self.base_path
        self.used_overlay = True

        self.run_external_program('umount {:s}'.format(self.working_path))

        shutil.rmtree(self.working_path, ignore_errors=True)
        shutil.rmtree(self.upper_path, ignore_errors=True)
        shutil.rmtree(self.overlay_path, ignore_errors=True)
        os.mkdir(self.upper_path)
        os.mkdir(self.overlay_path)
        os.mkdir(self.working_path)

        if (0 != self.run_external_program('mount -t overlay -o rw,lowerdir="{:s}",upperdir="{:s}",workdir="{:s}" overlay "{:s}"'.format(original_path,self.upper_path,self.overlay_path,self.working_path))):
            print(_("Failed to create the working environment at {:s} from {:s}").format(self.working_path,original_path))
            return True # error!!!

        # environment ready
        return False



    def prepare_working_path(self,final_path = None):

        """ Creates a working copy of the chroot environment to keep the original untouched.
            If final_path is None, will copy the compilation cache (base_path) to a working path; if not,
            will copy the bare minimum cache for shells (base_cache_path) to that path """

        self.upper_path = None
        self.overlay_path = None
        self.used_overlay = False

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


    def get_project_size(self):

        """ Calculates the size of all the files that will be installed in the final system """

        sum = 0
        final_path = os.path.join(self.working_path,"install_root")
        for dirname, dirnames, filenames in os.walk(final_path):
            for filename in filenames:
                sum += os.path.getsize(os.path.join(dirname,filename))

        self.program_size = sum
        print("Tamano: {%s}" % sum)


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
            # Check if it is a Meson project
        elif (os.path.exists(os.path.join(self.build_path,"meson.build"))):
            if self.build_meson():
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
            return self.run_chroot(self.working_path, 'bash -c "cd /project/install && cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=/usr/lib && make VERBOSE=1 && make DESTDIR=/install_root install"')
        else:
            return self.run_chroot(self.working_path, 'bash -c "cd /project/install && cmake .. -DCMAKE_INSTALL_PREFIX=/usr && make VERBOSE=1 && make DESTDIR=/install_root install"')


    def build_meson(self):

        install_path = os.path.join(self.build_path,"meson")
        if (os.path.exists(install_path)):
            shutil.rmtree(install_path,ignore_errors = True)
        os.makedirs(install_path)

        return self.run_chroot(self.working_path, 'bash -c "cd /project/meson && meson .. && mesonconf -Dprefix=/usr && ninja && DESTDIR=/install_root ninja install"')


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


    def run_external_program(self,command,show_msg = True):

        if show_msg:
            print(_("Launching {:s}").format(str(command)))
        proc = subprocess.Popen(command, shell=True)
        return proc.wait()


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
