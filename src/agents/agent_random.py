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

from random import choice

class Agent(object):
    def __init__(self,*kwargs):
        pass

    def getNext(self, mapref, current, goal, timeremaining):
        """returns random passable adjacent - agents are self-policing
        so must check cell passable from current in case of corner-cutting
        or may return invalid coord."""    
        adjacents = mapref.getAdjacents(current)
        possibles = [a for a in adjacents if mapref.isPassable(a,current)]
        return choice(possibles)

    def reset(self, **kwargs):
        pass
