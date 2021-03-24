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


AGENT_FILE = "agent_astar"       #agent filename - must be in src/agents/
#AGENT_FILE = "agent_random"     #agent filename - must be in src/agents/
MAP_FILE  = "../maps/bloodvenomfalls.map" 	#map filename - must be in maps (sister dir to src)
START     = (128,405)            #coordinates of start location in (col,row) format
GOAL      = (409,93)             #coordinates of goal location in (col,row) format

GUI = False                      #True = show GUI, False = run on command line
SPEED = 0.0                     #delay between displayed moves in seconds
DEADLINE = 15                   #Number of seconds to reach goal
HEURISTIC = 'octile'            #may be 'euclid' or 'manhattan' or 'octile' (default = 'euclid')
DIAGONAL = True                 #Only allows 4-way movement when False (default = True)
FREE_TIME = 0.000               #Step times > FREE_TIME are timed iff REALTIME = True
DYNAMIC = False                 #Implements runtime changes found in script.py when True
STRICT = True                   #Allows traversal of impassable cells when False (default = True)
PREPROCESS = False              #Gives agent opportunity to preprocess map (default = False)
#COST_MODEL = 'mixed_real'      #May be 'mixed' (default), 'mixed_real', 'mixed_opt1' or 'mixed_opt2'
COST_FILE = "../costs/G1-W5-S10.cost"

