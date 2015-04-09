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


AGENT_FILE = "agent_right"   #agent filename - must be in src/agents/
MAP_FILE  = "mixedcost3.map" #map filename - must be in maps (sister dir to src)
START     = (84,211)         #coordinates of start location in (col,row) format
GOAL      = (205,228)        #coordinates of goal location in (col,row) format


GUI = True                  #True = show GUI, False = run on command line
SPEED = 0.0                 #delay between displayed moves in seconds
DEADLINE = 15               #Number of seconds to reach goal
HEURISTIC = 'euclid'        #may be 'euclid' or 'manhattan'
DIAGONAL = True             #True = allow diagonal path, False = disallow
FREE_TIME = 0.000           #Steps greater than this are timed (if 0, all steps are timed)
