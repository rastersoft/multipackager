0.11 (2015/04/25)
 * Now keeps two caches, one with all the packages already installed in previous builds, and another (with a bare minimum system) for test shells, so the package creation process is much faster
 * Allows to specify the package revision in the command line
 * Allows to keep the temporary virtual machines used to build the packages
0.10 (2015/04/24)
 * Now ensures that the permissions and uid and gid in a package are the same than in the file system, to avoid conflicts in binary RPM packages
0.9 (2015/04/23)
 * Now the update of RPM caches works fine
 * Now copies fine the RPM binary packages, instead of copying the folder containing them
 * Now clears a classic MAKE project before building it
0.8 (2015/04/22)
 * Now supports alternative packages for deb (packagea | packageb)
0.7 (2015/04/20)
 * Now doesn't fail if the configure file doesn't exists.
 * Translated all sentences
0.6 (2015/04/19)
 * Added support for Fedora (RPM) packages
 * Allows to specify different triplets for binary and python projects
 * Takes into account the package name for python projects too
 * Allows to delete the caches
 * Added missing dependencies
 * Bug fixes
0.5 (2015/04/18)
 * Better command line parsing options
 * Allows to mount several paths from the host machine inside the virtual machines
 * Now the installation doesn't fail if the dep_utils package isn't installed
 * Now generates the cache environment in all cases
0.4 (2015/04/15)
 * Now passes the destination folder to the **multipackager.sh** script
0.3 (2015/04/14)
 * Added manpage
 * Fixed little bugs in the python3 packages generation
0.2 (2015/04/14)
 * Added support for Python3 packages
0.1 (2015/04/14)
 * First public version
