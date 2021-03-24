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

# mixed (DEFAULT): one used in the contest using sqrt(2) for diagonals.
# straight: moves are 1*cost of destination.
# diagonal: moves are sqrt(2)*cost of destination.
# mixed-real: full center-to-center cost between source and destination cell.
# mixed-opt1: like mixed but optimized to 1.5.
# straight: moves are 1*cost of destination.
# diagonal: moves are 1.5*cost of destination.
# mixed-opt2: like mixed but optimized to 1.5*2.
COST_MODELS = ['mixed', 'mixed-real', 'mixed-opt1',
               'mixed-opt2', 'straight', 'diagonal']

# Construct parser object
# https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument
parser = argparse.ArgumentParser(description="P4 Path Planning Simulator - Version " + VERSION)
parser.add_argument('-version',
                    action='version',
                    version='P4 Path Planning Simulator ' + VERSION)
parser.add_argument("CFG_FILE",
                    nargs='?',
                    default="config.py",
                    help="name of configuration file")
parser.add_argument('-m', '--map', 
                    action='store',
                    dest='MAP_FILE',
                    help="map file or filename in movingai format. If filename is given, it is looked in ../maps/")
parser.add_argument('-s', '--start',
                    action='store',
                    dest='START',
                    help="start coords in (col,row) format")
parser.add_argument('-g', '--goal',
                    action='store',
                    dest='GOAL',
                    help="goal (target) coords in (col,row) format")
parser.add_argument('-a','--agent',
                    action='store',
                    dest='AGENT_FILE',
                    help="agent file or filename respecting the API. If filename is given it is looked in agents/")
parser.add_argument('-nd', '--no-diagonals',
                    action='store_false',
                    dest='DIAGONAL',
                    default=True,
                    help="disallow diagonal moves (default: %(default)s)")
parser.add_argument('-d', '--deadline',
                    action='store',
                    dest='DEADLINE',
                    default=0,
                    help="deadline in seconds; 0 no deadline (default: %(default)s).")
parser.add_argument('-gui', '--gui',
                    action='store_true',
                    dest='GUI',
                    default=False,
                    help="display GUI (default: %(default)s).")
parser.add_argument('-e', '--heuristic',
                    action='store',
                    dest='HEURISTIC',
                    default="euclid",
                    choices=['euclid', 'manhattan', 'octile'],
                    help="heuristic to use (default: %(default)s).")
parser.add_argument('-r', '--speed',
                    action='store',
                    dest='SPEED',
                    default=0,
                    help="speed rate (default: %(default)s).")
parser.add_argument('-f', '-free',
                    action='store',
                    dest='FREE_TIME',
                    default=0,
                    help="steps returned < FREE_TIME are untimed, i.e., counted as 0 secs (default: %(default)s).")
parser.add_argument('-cm', '--cost',
                    action='store',
                    dest='COST_MODEL',
                    default="mixed",
                    choices = COST_MODELS,
                    help="cost model to use (default: %(default)s).")
parser.add_argument('-c', '--cost-file',
                    action='store',
                    dest='COST_FILE',
                    help="file with cost of cells")
parser.add_argument('-dy', '-dynamic', '--dynamic',
                    action='store_true',
                    dest='DYNAMIC',
                    default=False,
                    help="make changes based on script.py (default: %(default)s).")
parser.add_argument('-ns', '-nonstrict', '--nonstrict',
                    action='store_false',
                    dest='STRICT',
                    default=True,
                    help="allow agent to traverse impassable cells, albeit at infinite cost (default: %(default)s).")
parser.add_argument('-pre', '--preprocess',
                    action='store_true',
                    dest='PREPROCESS',
                    default=False,
                    help="calls agent.preprocess() before starting search (default: %(default)s).")
parser.add_argument('-rt', '-realtime', '--realtime',
                    action='store_true',
                    dest='REALTIME',
                    default=False,
                    help="time every step instead of just first step (default: %(default)s).")
parser.add_argument('-b', '-batch', '--batch',
                    nargs='*',
                    dest='BATCH',
                    action='store',
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
