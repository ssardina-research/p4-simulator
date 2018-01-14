#! /usr/bin/env python2.7

# Copyright (C) 2014-17 Peta Masters and Sebastian Sardina
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

"""
This script allows to simulate an agent moving in a grid in real-time. Agents can be implemented in any way and may
rely on path-planners, for which the framework provides the basic API.

More information please refer to https://bitbucket.org/ssardina/soft-p4-sim-core
"""

import argparse, os, textwrap
import p4_controller
import re
import logging
import p4_utils
from p4_utils import * # sets constants


# Construct parser object
parser = argparse.ArgumentParser(description="P4 Path Planning Simulator - Version " + VERSION)
parser.add_argument("CFG_FILE", nargs='?', default="config.py", help="name of configuration file")
parser.add_argument('-m', action='store', dest='MAP_FILE', help="map filename")
parser.add_argument('-s', action='store', dest='START', help="start coords")
parser.add_argument('-g', action='store', dest='GOAL', help="goal (target) coords")
parser.add_argument('-a', action='store', dest='AGENT_FILE', help="agent filename")
parser.add_argument('-nodiag', action='store_false', dest='DIAGONAL', default=True,
                    help="disallow diagonal moves (default diagonals allowed)")
parser.add_argument('-d', action='store', dest='DEADLINE', default=0, help="deadline in seconds")
parser.add_argument('-gui', action='store_true', dest='GUI', default=False, help="display gui (default false)")
parser.add_argument('-e', action='store', dest='HEURISTIC', default="euclid", help="euclid, manhattan, or octile")
parser.add_argument('-r', action='store', dest='SPEED', default=0, help="speed (rate)")
parser.add_argument('-f', action='store', dest='FREE_TIME', default=0,
                    help="steps returned <FREE_TIME are untimed, i.e., counted as 0 secs (default to 0.005)")
parser.add_argument('-cm', action='store', dest='COST_MODEL', default="mixed",
                    help="mixed, mixed-real, mixed-opt1, or mixed-opt2")
parser.add_argument('-c', action='store', dest='COST_FILE', help="file with cost of cells")
parser.add_argument('-version', action='version', version='P4 Path Planning Simulator ' + VERSION)
parser.add_argument('-dynamic', action='store_true', dest='DYNAMIC', default=False,
                    help="make changes based on script.py (default false)")
parser.add_argument('-nonstrict', action='store_false', dest='STRICT', default=True,
                    help="allow agent to traverse impassable cells, albeit at infinite cost")
parser.add_argument('-pre', action='store_true', dest='PREPROCESS', default=False,
                    help="give agent opportunity to preprocess map")
parser.add_argument('-realtime', action='store_true', dest='REALTIME', default=False,
                    help="time every step (default false)")
parser.add_argument('-batch', nargs='*', dest='BATCH', action='store',
                    help="run scenario in batch mode. Requires .scen file and .csv file for results. Optionally takes "
                         "integer as 3rd argument for number of repetitions across which test times are to be averaged.")
args = parser.parse_args()

# If batch mode, then check scenario and agent files are supplied, extract map path from path of scenario file
if args.BATCH is not None:
    # Requires .scen file and agent file to run
    if not len(args.BATCH) >= 2:
        logging.error("-batch takes minimum of 2 arguments. Terminating...")
        raise SystemExit
    elif not os.path.isfile(args.BATCH[0]):
        logging.error("Scenario file " + args.BATCH[0] + " not found. Terminating...")
        raise SystemExit
    elif args.AGENT_FILE is None:
        logging.error("Agent file not supplied. Terminating...")
        raise SystemExit
    else:
        # Extract path of map file from path of scenario (just remove suffix .scen)
        fn = os.path.split(args.BATCH[0])[1]
        # extract map pathname: everything up to .map included
        try:
            args.MAP_FILE = re.match(r'(.*\.map).*', args.BATCH[0]).group(1)
        except AttributeError:
            args.MAP_FILE = ''
        logging.info(args.MAP_FILE)
        logging.info("BATCH mode to be run in map {} (cost file: {}) with agent {}".format(args.MAP_FILE, args.COST_FILE,
                                                                                           args.AGENT_FILE))



    # If map file named available (command line or batch mode), take it. Otherwise, use one in config file
if args.MAP_FILE is not None:
    # If map file is named but does not exist, raise exception and terminate
    dirname = os.path.dirname(args.MAP_FILE)
    basename = os.path.basename(args.MAP_FILE)
    if not dirname:
        # if no directory is specified, assume ../maps/
        dirname = '../maps/'
    else:
        dirname = dirname + '/'
    if not os.path.isfile(dirname + basename):
        logging.error(dirname + basename + " not found. Terminating ... ")
        raise SystemExit

    CFG_FILE = None
    # display initial settings - may be defaults (before config file) or from CLI
    print
    "\n" + str(args)[9:] + "\n"  # skip 1st 9 chars of output

else:  # assume using config file, not command line arguments
    logging.info("Checking for configuration file: " + args.CFG_FILE)
    # If given config file does not exist, raise exception and terminate
    if not os.path.isfile(args.CFG_FILE):
        logging.error(args.CFG_FILE + " not found. Terminating ... ")
        raise SystemExit

    CFG_FILE = args.CFG_FILE

# Launch simulator, passing in validated config filename
# note - passes args (typically defaults), even if config file named
s = p4_controller.SimController(CFG_FILE, vars(args))
