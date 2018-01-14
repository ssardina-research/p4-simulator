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

import signal
import os
from math import sqrt
import logging

# MIN TEXT
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                    datefmt='%H:%M:%S')

# FULL TEXT
# logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
#                     datefmt='%a, %d %b %Y %H:%M:%S')

# Version of P4
VERSION = "3.5.0"

# P4 CONSTANTS
COL_OL = "red"       # open list
COL_CL = "yellow"    # closed list
COL_PP = "azure"     # proposed path
COL_EX = "purple"    # extra set
RESET = "reset"      # reset to current map data
COL_START = "green"  # cross at start pos
COL_GOAL = "tomato"  # cross at goal pos

TIMER = "clock"      # default timer - may be clock or time
#SQRT2 = sqrt(2)
#SQRT2 = 1.4
SQRT2 = 1.414
COL = 0
ROW = 1
INF = float('inf')

# positions within node
F_POS = 0   # f val
G_POS = 1   # g cost so far
C_POS = 2   # current coord, formatted (col,row)
P_POS = 3   # parent coord, formatted (col,row)

def addVectors(a,b):
    return (a[0]+b[0],a[1]+b[1])
    
def getBlock(topleft,botright):
    """Returns list of coordinates in nominated block - domain agnostic"""
    a1, a2 = topleft
    b1, b2 = botright
    #TODO - appropriate list comprehension eludes me!
    L=[]
    for x in range(a1,b1+1):
        for y in range(a2,b2+1):
            L.append((x,y))
    return L

class BadMapException(Exception):
    pass
    
class BadAgentException(Exception):
    pass
    
class BadConfigException(Exception):
    pass
	
    
class Timeout():
    """Timeout class using ALARM signal. Imported for Unix os only.
       Code adapted from http://stackoverflow.com/questions/8464391.
       enter and exit classes to allow for 'with' construction. """

    class Timeout(Exception): pass

    def __init__(self, sec):
        self.sec = int(sec)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.sec)

    def __exit__(self, *args):
        signal.alarm(0)  # disable alarm

    @staticmethod
    def raise_timeout(*args):
        raise Timeout.Timeout()


class WinTimeout():
    """Placeholder timeout class imported for Windows only. Rather than test os
       every time getNext() is called on the Agent, use of alias with drop through means
       nothing is tested at runtime."""
    class Timeout(Exception): pass
    
    def __init__(self, sec):
        pass

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

