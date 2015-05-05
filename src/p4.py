#! /usr/bin/env python2.7

# Copyright (C) 2014 Peta Masters and Sebastian Sardina
#
# This file is part of "P4-Simulator" package.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import argparse, os, textwrap
import p4_controller

# Version of P4
VERSION = "2.1"

# Construct parser object
parser = argparse.ArgumentParser(description="P4 Path Planning Simulator - Version " + VERSION)
parser.add_argument("CFG_FILE", nargs='?', default="config.py", help="name of configuration file")
parser.add_argument('-m', action='store', dest='MAP_FILE', help="map filename")
parser.add_argument('-s', action='store', dest='START', help="start coords")
parser.add_argument('-g', action='store', dest='GOAL', help="goal (target) coords")
parser.add_argument('-a', action='store', dest='AGENT_FILE', help="agent filename")
# Note, by default DIAGONAL is true. If -nodiag is set, DIAGONAL becomes false.
parser.add_argument('-nodiag', action='store_false', dest='DIAGONAL', default=True, help="disallow diagonal moves (default diagonals allowed)")
parser.add_argument('-d', action='store', dest='DEADLINE', default=0, help="deadline in seconds")
parser.add_argument('-gui', action='store_true', dest='GUI', default = False, help="display gui (default false)")
parser.add_argument('-e', action='store', dest='HEURISTIC', default="euclid", help="euclid, manhattan, or octile")
parser.add_argument('-r', action='store', dest='SPEED', default=0, help="speed (rate)")
parser.add_argument('-f', action='store', dest='FREE_TIME', default=0, help="steps returned <FREE_TIME are untimed, i.e., counted as 0 secs (default to 0.005)")
parser.add_argument('-auto', action='store_true', dest='AUTO', default=False, help="running automatically (default false)")
parser.add_argument('-version', action='version', version='P4 Path Planning Simulator ' + VERSION)
parser.add_argument('-dynamic', action='store_true', dest='DYNAMIC', default=False, help="make changes based on script.py (default false)")
# Note, similar to DIAGONAL above. By default STRICT is true and impassable cells cannot be traversed. Use of -nonstrict, sets it to false.
parser.add_argument('-nonstrict', action='store_false', dest='STRICT', default=True, help="allow agent to traverse impassable cells, albeit at infinite cost")

args = parser.parse_args()

#if map file named, assume using command line arguments, not config file
if args.MAP_FILE is not None:
    # If map file is named but does not exist, raise exception and terminate
    if not os.path.isfile('../maps/' + args.MAP_FILE):
        print(args.MAP_FILE + " not found. Terminating ... ")
        raise SystemExit
        
    CFG_FILE = None
    if args.AUTO is False:
        #display initial settings - may be defaults (before config file) or from CLI
        print "\n" + str(args)[9:] + "\n"   #skip 1st 9 chars of output
    
else:  #assume using config file, not command line arguments 
    if args.AUTO is False:
        print("Checking for configuration file: " + args.CFG_FILE)
    # If given config file does not exist, raise exception and terminate
    if not os.path.isfile(args.CFG_FILE):
        print(args.CFG_FILE + " not found. Terminating ... ")
        raise SystemExit

    CFG_FILE = args.CFG_FILE

# Launch simulator, passing in validated config filename
# note - passes args (typically defaults), even if config file named
s = p4_controller.SimController(CFG_FILE, vars(args))
