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

class configuration:

    def __init__(self,project_path):

        self.project_path = project_path
        self.distros = []
        self.cache_path = "/var/opt/multipackager"
        self.working_path = "/root/multipackager"
        self.shell = "/bin/bash"


    def delete_distros(self):

        self.distros = []


    def append_distro(self, distro, name,architecture):

        self.distros.append({"distro":distro, "name":name, "architecture":architecture})


    def read_config_file(self,file = None):

        has_error = False;

        try:
            if (file == None):
                cfg = open(os.path.join("/etc","multipackager","config.cfg"),"r")
            else:
                cfg = open(file,"r")
        except:
            print("Can't find the configuration file")
            return True

        line_counter = 0
        for line in cfg:
            line_counter += 1
            line = line.replace("\n","").replace("\r","")
            if ((line == "") or (line[0] == "#")):
                continue
            parameters = line.split(" ")
            nparams = len(parameters)
            if (parameters[0] == "distro:"):
                if (nparams != 4):
                    print ("Error in line {:d}; incorrect number of parameters\n".format(line_counter))
                    has_error = True;
                    continue
                if ((parameters[1] != "debian") and (parameters[1] != "ubuntu")) :
                    print ("Error in line {:d}: {:s} is not a valid linux distribution\n".format(line_counter,parameters[1]))
                    has_error = True;
                    continue
                self.append_distro(parameters[1], parameters[2], parameters[3])
            elif (parameters[0] == "cache_path:"):
                if (nparams != 2):
                    print ("Error in line {:d}; incorrect number of parameters\n".format(line_counter))
                    has_error = True;
                    continue
                self.cache_path = parameters[1]
            elif (parameters[0] == "working_path:"):
                if (nparams != 2):
                    print ("Error in line {:d}; incorrect number of parameters\n".format(line_counter))
                    has_error = True;
                    continue
                self.working_path = parameters[1]
            elif (parameters[0] == "shell:"):
                if (nparams != 2):
                    print ("Error in line {:d}; incorrect number of parameters\n".format(line_counter))
                    has_error = True;
                    continue
                self.shell = parameters[1]
        return has_error