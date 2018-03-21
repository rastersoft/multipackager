# History of versions #

* Version 0.32 (2018/02/28)
  * Now using the OR option in debian control file to choose between two packages works fine
* Version 0.31 (2017/11/26)
  * Now does an 'apt update' before installing dependencies for a package
  * Now doesn't wait for the user to press 'y' when installing meson
* Version 0.30 (2017/01/22)
  * Added support for Meson builder projects
  * Allows to update in a single command all the distros based on the type (e.g. Update all debian distros)
* Version 0.28 (2016/09/26)
  * Installs all the packages needed also in RPM
* Version 0.27 (2016/09/25)
  * Now doesn't fail when debian dependencies have a version number requirement
* Version 0.26 (2016/09/19)
  * Installs all the packages needed for a project, instead of installing only the building ones
* Version 0.25 (2016/09/06)
  * Allows to specify different configuration folders for Debian/Ubuntu 32 and 64 bits
* Version 0.24 (2016/08/25)
  * Now shows the current distro being compiled in the terminal's titlebar
  * Now shows the chroot path for the current shell in the terminal's titlebar
  * Now the make for CMake projects is verbose
* Version 0.23 (2016/07/17)
  * Now ensures that any OverlayFS has been unmounted before trying to mount it again (could happen in previous version if multipackager is interrupted and launched again)
* Version 0.22 (2016/05/10)
  * Now uses OverlayFS to speed up all the operations, avoiding the full copy of the images (for backing up purposes) before doing any operation
* Version 0.21 (2015/11/08)
  * Now uses DNF for fedora 22 and greater, instead of YUM
* Version 0.20 (2015/10/29)
  * Now doesn't fail if the *build* folder doesn't exists in binary projects
* Version 0.19 (2015/10/26)
  * Now removes the *build* folder in python3 projects when building for ARCH, so it won't fail
* Version 0.18 (2015/09/29)
  * Now can install, in ARCH, dependencies from AUR for local packages
* Version 0.17 (2015/09/27)
  * Removed the 'sync' commands, which speeds up the work.
  * Now adds the package size in debian packages
* Version 0.16 (2015/08/30)
  * Allows to install local packages before creating a package. Useful when creating a package that depends of another local project.
  * Now, when the creation of a package fails, the system won't fail, but continue with the other OSs and, at the end, show which ones failed.
* Version 0.15 (2015/08/24)
  * Added support for both the old and new URI format for AUR repository (ARCH Linux)
  * Now automagically downloads the GPG keys (ARCH Linux)
  * Now only uses the makedeps for python projects in Pacman packages
* Version 0.14 (2015/05/16)
  * Added support for Pacman, the Arch's package manager.
* Version 0.13 (2015/05/09)
  * Now doesn't ask if the user wants to continue when updating a Fedora system
* Version 0.12 (2015/04/26)
  * Fixed a bug when launching a shell without specifying a linux distribution type and name
* Version 0.11 (2015/04/25)
  * Now keeps two caches, one with all the packages already installed in previous builds, and another (with a bare minimum system) for test shells, so the package creation process is much faster
  * Allows to specify the package revision in the command line
  * Allows to keep the temporary virtual machines used to build the packages
* Version 0.10 (2015/04/24)
  * Now ensures that the permissions and uid and gid in a package are the same than in the file system, to avoid conflicts in binary RPM packages
* Version 0.9 (2015/04/23)
  * Now the update of RPM caches works fine
  * Now copies fine the RPM binary packages, instead of copying the folder containing them
  * Now clears a classic MAKE project before building it
* Version 0.8 (2015/04/22)
  * Now supports alternative packages for deb (packagea | packageb)
* Version 0.7 (2015/04/20)
  * Now doesn't fail if the configure file doesn't exists.
  * Translated all sentences
* Version 0.6 (2015/04/19)
  * Added support for Fedora (RPM) packages
  * Allows to specify different triplets for binary and python projects
  * Takes into account the package name for python projects too
  * Allows to delete the caches
  * Added missing dependencies
  * Bug fixes
* Version 0.5 (2015/04/18)
  * Better command line parsing options
  * Allows to mount several paths from the host machine inside the virtual machines
  * Now the installation doesn't fail if the dep_utils package isn't installed
  * Now generates the cache environment in all cases
* Version 0.4 (2015/04/15)
  * Now passes the destination folder to the **multipackager.sh** script
* Version 0.3 (2015/04/14)
  * Added manpage
  * Fixed little bugs in the python3 packages generation
* Version 0.2 (2015/04/14)
  * Added support for Python3 packages
* Version 0.1 (2015/04/14)
  * First public version
