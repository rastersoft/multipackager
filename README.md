# MULTIPACKAGER #

Simplifies the creation of Linux packages for multiple architectures and distributions.

Multipackager is a program that aims to simplify the creation of packages for linux distributions. To do so, it automatizes the creation of virtual machines with specific distributions, versions and architectures, and the compilation and packaging process for each one. It allows to create packages for i386 and amd64 for any available version of Debian and Ubuntu.


## USAGE ## 

    **multipackager.py** project_folder *[--config config_file]*
    **multipackager.py** project_folder *[--config config_file]* {debian|ubuntu} version_name {i386|amd64} 
    **multipackager.py** shell *[--config config_file]* vm_folder {i386|amd64} 
    **multipackager.py** shell *[--config config_file]* vm_folder {debian|ubuntu} version_name {i386|amd64} 
    **multipackager.py** update *[--config config_file]* 
    **multipackager.py** update *[--config config_file]* {debian|ubuntu} version_name {i386|amd64} 


## INSTALATION ##

Multipackager uses python setup, so just do:

    sudo ./setup.py install

Multipackager have the following dependencies:

    python 3
    debootstrap
    systemd

Debootstrap is used to generate the basic CHROOT environment for the distros; systemd is needed to launch the virtual machines and keep them isolated (something that the basic CHROOT can't do).


## HOW DOES IT WORK? ##

Multipackager uses Debootstrap to automatically download and generate several virtual machines for the desired distros, versions and architectures. After that, it automatically compiles the specified project's source code for each one, and creates the corresponding package.

Each virtual machine is defined by a triplet of distribution type, distribution name and architecture. Currently only "debian" and "ubuntu" are supported, and "i386" and "amd64" for architecture. Examples of these triplets are:

    debian jessie i386
    debian sid amd64
    ubuntu utopic amd64
    ubuntu trusty i386

The first time a triplet is specified, multipackager will create a base version in an internal cache (stored at **/var/opt/multipackager**), and will use it the next times to reduce the creation time. This cached version has only the base system; each time a new package is created, a working copy of this base system is made, where the dependencies are installed and the project is built, thus keeping the cached base system pristine. Of course, it is possible to do an update of the base cached base system to ensure that the latest packages are used.

By default, the working copies are created at **/root/multipackager**, but it is possible to set a different folder in a configuration file (more on this later). The use of the root folder is because multipackager must be run as root, because it launches chroot-based virtual machines.

After the working copy is created, the project's folder is copied inside and a virtual machine is launched. Inside it, multipackager will install the dependencies for the project, compile it and build the package. Multipackager can determine automagically the build system (pydev, make, cmake, autoconf/automake...).

The created packages are stored in the current folder. Also, if a package already exists, it won't be created again, but will be skipped. This allows to just relaunch multipackager with the same parameters if, due to an error, the creation of one architecture or OS version fails but not the previous ones.

This process is repeated for each of the triplets configured in the configuration file.


## THE CONFIGURATION FILE ##

The configuration file is stored, by default, at **/etc/multipackager/config.cfg**, and is a file with the following structure:

    distro: type name architecture  
    distro...  
    cache_path: path  
    working_path: path  
    shell: path/program

All the lines are optional.

Each **distro** line contains a distro triplet, specifying an OS to which, by default, we want to build packages. We can specify as many distros as we want.

The **cache_path** specifies where to store the cached base systems. If this line doesn't exists, multipackager will use **/var/opt/multipackager**.

The **working_path** specifies where to store the working virtual machines. If this line doesn't exists, multipackager will use **/root/multipackager**.

The **shell** specifies which shell to use when launching a manual environment (more on this later). By default it is **/bin/bash**.


## PREPARING THE PROJECT ##


Multipackager needs some folders and files already available in the project folder. The first and most important for binary projects is the **debian** (or **Debian**, or **DEBIAN**) folder, with the **control** file ( https://www.debian.org/doc/debian-policy/ch-controlfields.html ). This file must have **Depends** and **Build-Depends** fields to allow multipackager to install the needed packages during the build process. Also, it is mandatory to include a field **Architecture: any**, which multipackager will replace with **Architecture: x86** or **Architecture: x86_64** as needed. If the field is **Architecture: all**, it won't be modified.

There can be, optionally, an **ubuntu** (or **Ubuntu**, or **UBUNTU**) folder with the same files. When creating packages for a Debian system, only the former folders would be used; when creating for an Ubuntu system, if the later exists, them will be used; if not, the former will be used.

For python3 projects, the most important files are **setup.py** (which must be adapted for **DistUtils**) and **stdeb.cfg**, which contains both the final dependencies AND the build dependencies. About this, multipackager automatically adds **python3, python3-all, python3-stdeb, python-all** and **fakeroot**, so you must add only other needed dependencies (like, in the case or multipackager, *pandoc*, used to convert the README.md file to manpage format).

In order to build the project itself and do the final installation, multipackager will follow these rules, and use **ONLY the first one** that applies:

 * if a file called **multipackager_XXXXX.sh** exists in the project folder (with XXXXX being the distro name; e.g. *multipackager_debian.sh*), multipackager will run it, passing as the first and only parameter the **DESTDIR** path (e.g.: *multipackager_ubuntu.sh /install_root*).

 * if a file **multipackager.sh** exists in the project folder, multipackager will run it, passing as the first and only parameter the **DESTDIR** path (e.g.: *multipackager.sh /install_root*).

 * if a file **setup.py** exists in the project folder, multipackager will presume that it is a python3 project, and will run **python3 setup.py --command-packages=stdeb.command bdist_deb** to build the package and install it in the **install_root** folder.

 * if a file **configure** exists in the project folder, multipackager will presume that it is an autoconf/automake project and will run **./configure --prefix=/usr && make && make DESTDIR=/install_root install** to build the package and install it in the **install_root** folder.

 * if a file **autogen.sh** exists in the project folder, multipackager will presume that it is an autoconf/automake project that hasn't been configured yet, so will run **./autogen.sh**, and then will run **./configure --prefix=/usr && make && make DESTDIR=/install_root install** to build the package and install it in the **install_root** folder.

 * if a file **CMakeLists.txt** exists in the project folder, multipackager will presume that it is a CMake project, so will create an **install** folder an run inside it **cmake .. -DCMAKE_INSTALL_PREFIX=/usr && make && make DESTDIR=/install_root install** to build the package and install it in the **install_root** folder.

 * finally, if a file **Makefile** exists in the project folder, multipackager will presume that it is a classic Makefile project, and will run **make && make PREFIX=/usr DESTDIR=/install_root install** to build the package and install it in the **install_root** folder.


## DETAILED USAGE ##

There are several options:

**multipackager.py** project_folder *[--config config_file]*  
**multipackager.py** project_folder *[--config config_file]* {debian|ubuntu} version_name {i386|amd64}  

These two commands specifies to build packages for a project. The first one will build packages for the project stored at **project_folder**, and for all the OS triplets specified in the default config file (unless another **config_file** is specified; in that case the triplets will be searched inside it). This way, an user can define all the common triplets he/she uses commonly, and build the packages in a single command.

The second command allows to build a package for a project for an specific OS triplet.

**multipackager.py** shell *[--config config_file]* vm_folder {i386|amd64}  
**multipackager.py** shell *[--config config_file]* vm_folder {debian|ubuntu} version_name {i386|amd64}  

These two commands allow to launch an interactive shell inside a virtual machine. The first one needs that the folder with the virtual machine files (**vm_folder**) already exists. The second one checks if the folder exists: if it doesn't exist, will copy the base system (from the cache if it already exists, or from the server if there is no cached version) to the specified folder, and launch an interative shell inside it; if it exists, will work like the previous command. In both cases, specifying the architecture is a must.

Since the vm_folder is not deleted, and is reused if it already exists, this allows to enter a virtual machine, do something, exit, and enter again and do more things.

These virtual machines are useful to do manual compilation tests and other things, and they are created very fast (if they are already cached, of course).

**multipackager.py** update *[--config config_file]*  
**multipackager.py** update *[--config config_file]* {debian|ubuntu} version_name {i386|amd64}  

These last two commands allow to update the cached base systems, to ensure that they have the last versions of the packages. The first one will update all the triplets stored in the default config file (or in the alternative **config_file**); the second one will update only the specified triplet.


## CONTACTING THE AUTHOR ##

Sergio Costas Rodríguez (Raster Software Vigo)  
raster@rastersoft.com  
rastersoft@gmail.com  
http://www.rastersoft.com
