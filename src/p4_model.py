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

from math import fabs, sqrt 
from random import randint
from collections import deque


class LogicalMap(object):
    """
    Logical representation of the map, allows it to be interrogated by other components.
    This version returns float('inf') for non-traversable cells.
    """

    def __init__(self, mappath=None, costpath=None):
        """Constructor. Sets default method calls, initialises class attributes,
           calls _readMap()"""
        self.SQRT2 = sqrt(2)
        self.SQRT05 = sqrt(.5)
        self.OCT_CONST = self.SQRT2 - 1
        DEFAULT_HEIGHT = 512
        DEFAULT_WIDTH = 512
        self.uniform = True
        
        self.cellWithinBoundaries = self.isMapped  # for backward compatibility

        # Default method calls. If getH() is called, by default run euclid(), etc.
        self.getH = self._euclid
        self.getAdjacents = self._getDiagAdjacents
        self.isAdjacent = self._isDiagAdjacent
        self.getCost = self._getDiagCost
        self.neighbours = []

        # terrain types and default costs as per http://movingai.com/benchmarks/formats.html
        # water is untraversable in general, unless coming from water itself (see below)
        self.terrains = {"ground" : "G", "ground1" : ".", "water" : "W", "swamp" : "S", "tree" : "T"}
        self.costs = {".": 1, "G": 1, "0": float('inf'), "@": float('inf'), "S": 1, "T": float('inf'), "W": float('inf')}
                      
        # dictionary to hold precalculated costs for straight and diagonal moves between terrain types
        self.mixedmatrix = {}
        
        self.neighbourDic = {}

        # Each key is store in the map as (key_location) : [ d1, d2, ... ] where d1, d2, ... are the location of
        # the door.
        self.key_and_doors = {}

        if mappath is not None:
            # print("Opening " + mappath)
            self._readMap(mappath, costpath)
            # if readMap fails, SystemExit reports to command line and quits
            if self.matrix is None:
                print("Failed to load file!\n")
                raise SystemExit
        else:
            # if mappath == None, readMap not attempted and default-sized matrix is all set to '.'
            self.matrix = [["." for col in range(DEFAULT_WIDTH)]
                           for row in range(DEFAULT_HEIGHT)]
            self.info = {"height": DEFAULT_HEIGHT, "width": DEFAULT_WIDTH}
            self.costs["."] = 1
            self.mixedmatrix[".",".",True] = self.SQRT2
            self.mixedmatrix[".",".",False] = 1
            
    def _getDiffAdjs(self, coord):
        """returns adjacents with different cost from cell passed in as coord
        :type coord: tuple
        """
        diffs = []
        cost = self.costs[self.getCell(coord)]
        adjlist = self.getAdjacents(coord)
        for adj in adjlist:
            if not self.costs[self.getCell(adj)] == cost:
                diffs.append(adj)
        return diffs

    def _hasDiffAdj(self, coord):
        """returns true if any adjacent has different cost from cell passed in as coord
        :type coord: tuple
        """
        cost = self.costs[self.getCell(coord)]
        adjlist = self.getAdjacents(coord)
        for adj in adjlist:
            if not self.costs[self.getCell(adj)] == cost:
                return True
        return False

    def hasDiffAdj(self, coord):
        """ precondition: must have run preprocessMap. Returns result by direct query
        to neighbours"""
        return self.neighbours[coord[0]][coord[1]]

    def getDiffAdjs(self, coord):
        """  precondition: must have run preprocessMap. Returns result by direct query
        to neighbourDic"""
        return filter(self.isPassable, self.neighbourDic[coord])

    def setHeuristic(self, h="euclid"):
        """Explicitly set method used when getH() is called."""
        if h == "euclid":  
            self.getH = self._euclid
        elif h == "octile":
            self.getH = self._octile
        else:
            self.getH = self._manhattan
            
    def setCostModel(self, cm="mixed"):
        """Sets straight and diagonal multipliers based on whichever cost model is in use."""
        if cm == "mixed":
            self.straightmulti = 1
            self.diagmulti = self.SQRT2
        elif cm == "mixed_opt1":
            self.straightmulti = 1
            self.diagmulti = 1.5
        elif cm == "mixed_opt2":
            self.straightmulti = 2
            self.diagmulti = 3
        else:
            self.getCost = self._getRealCost      

    def setCostCells(self, costCells={}):
        """Sets the cost of cells as per costCells- if missing, leave existing cost """
        for terrain in (set(costCells.keys()).intersection(self.terrains.keys())):
            abbrev = self.terrains[terrain]
            self.costs[abbrev] = costCells[terrain]

    def setDiagonal(self, d):
        """Explicitly set methods to be used when getAdjacents() or isAdjacent() called."""
        if d is None or d:  # default
            self.getAdjacents = self._getDiagAdjacents
            self.isAdjacent = self._isDiagAdjacent
            self.getCost = self._getDiagCost
        else:
            self.getAdjacents = self._getNonDiagAdjacents
            self.isAdjacent = self._isNonDiagAdjacent
            self.getCost = self._getNonDiagCost

    def getCell(self, (col, row)):
        """Returns character at (col, row) representing type of terrain there. Returns @ (oob) if call fails
        :type col: int
        :type row: int
        """
        try:
            return self.matrix[col][row]
        except:
            return '@'
        
    def isKey(self, position):
        """
        Return true if and only if the (col,row) is a key.
        :type row: int
        :type col: int
        :rtype : bool
        :return:
        """
        (col, row) = position
        return (col, row) in self.key_and_doors.keys()

    def isDoor(self, position):
        """
        Return true if and only if the (col,row) is a door.
        :rtype : bool
        :type row: int
        :type col: int
        :return:
        """
        (col, row) = position
        for k in self.key_and_doors:
            if (col, row) in self.key_and_doors[k]:
                return True
        return False

    def hasKeyForDoor(self, door, keys):
        """
        :param door: The door coordinate.
        :param keys: The list of available keys.
        :return: True iff agent has the key for the door.
        """
        if keys is None:
            return False
        for k in keys:
            if door in self.key_and_doors[k]:
                return True
        return False      
    
    def _getDiagCost(self, coord, previous=None, keys=None):
        """Returns the cost of the terrain type at coord, read from costs dictionary.
        If previous supplied, return val based on relative locations to prohibit corner-cutting
        Appropriate multiplier (for straights and diagonals) comes from setCostModel()
        """
        if self.isDoor(coord) and not self.hasKeyForDoor(coord, keys):
            return float('inf')

        # get the terrain type for coord
        coord_type = self.getCell(coord)
        
        if previous:
            # for uniform-cost maps, water is only navigable from other water
            isDiagonalMove = self.isDiag(previous, coord)
            if self.uniform and coord_type == "W" and self.getCell(previous) == "W":
                if isDiagonalMove:
                    return self.diagmulti * self.costs['G']
                else:
                    return self.straightmulti * self.costs['G']
            if isDiagonalMove:
                if self.cutsCorner(previous, coord, keys):
                    return float('inf')
                else:
                    return self.diagmulti * self.costs[coord_type]
            else:
                return self.straightmulti * self.costs[coord_type]
        else:
            return self.costs[coord_type]

    def _getRealCost(self, coord, previous=None, keys=None):
        """
        Called as getCost() when mixed-real cost model is selected. Returns the cost of 
        the terrain type at coord, read from costs dictionary.
        If previous supplied, checks for corner-cutting and provides straight/diagonal 
        cost based on terrain type, read from mixed cost dictionary.
        """

        if self.isDoor(coord) and not self.hasKeyForDoor(coord, keys):
            return float('inf')

        # get the terrain type for coord
        coord_type = self.getCell(coord)
 
        if previous:
            isDiagonalMove = self.isDiag(previous, coord)
            if isDiagonalMove and self.cutsCorner(previous, coord, keys):
                    return float('inf')
            else:
                previous_type = self.getCell(previous)
                return self.getMixedCost(previous_type, coord_type, isDiagonalMove)
        else:
            return self.costs[coord_type]
        
    def cutsCorner(self, previous, coord, keys=None):
        """ returns true if diagonal move cuts corner, false otherwise. Calling program must verify that this is a diagonal move before calling cutsCorner()"""
        coord_x, coord_y = coord
        previous_x, previous_y = previous
        dX = previous_x - coord_x
        dY = previous_y - coord_y
        if self.isCellTraversable((coord_x, coord_y + dY), keys=keys) and self.isCellTraversable((coord_x + dX, coord_y), keys=keys):
            return False
        else:
            return True
            
    def _getNonDiagCost(self, coord, previous=None, keys=None):
        #TODO: is this correct? what about water-to-water for uniform grids?
        """
        Returns the cost of the terrain type at coord, read from costs dictionary.
        :type previous: (int,int)
        :type coord: (int,int)
        :param coord: The coordinates
        :param previous:  The previous coordinates. If previous supplied, calc based on relative locations
        :rtype : float
        TODO - bring this into line with new _getDiagCost!!!!!!!!!!!!!! - i.e.4 x cost models, etc.
        """
        if previous and self.isDiag(previous, coord):
            return float('inf')
        else:
            return self.costs[self.getCell(coord)]
            
    @property
    def height(self):
        """
        Returns height of map based on number of characters in first row, which may
        differ from map header. Note characters are reorganised to read back as col,row
        :rtype : int
        """
        return len(self.matrix[0])

    @property
    def width(self):
        """
        Returns width of map based on number of rows, which may differ from
        map header. Note characters are reorganised to read back as col,row
        :rtype : int
        """
        return len(self.matrix)

    @staticmethod
    def isDiag(a, b):
        """
        Returns true if these adjacent coordinates are on a diagonal
        :type b: (int,int)
        :type a: (int,int)
        :rtype : bool
        """
        return (fabs(a[0] - b[0]) == 1) and (fabs(a[1] - b[1]) == 1)

    @staticmethod
    def _isDiagAdjacent(a, b):
        """Internal. Checks 8 ways. Called as isAdjacent() when DIAGONAL set to True"""
        return (fabs(a[0] - b[0]) <= 1) and (fabs(a[1] - b[1]) <= 1)

    @staticmethod
    def _isNonDiagAdjacent(a, b):
        """Internal. Checks 4 ways. Called as isAdjacent() when DIAGONAL set to False"""
        return (a[0] == b[0] and fabs(a[1] - b[1]) == 1) or (a[1] == b[1] and fabs(a[0] - b[0]) == 1)

    def isCellTraversable(self, coord, keys=None):
        """
        Returns whether coord cell is traversable by itself or not
        """
        # if there is a door in coord but we don't have the key, then it is not traversable
        if self.isDoor(coord) and not self.hasKeyForDoor(coord, keys):
            return False
        else:
            return self.costs[self.getCell(coord)] < float('inf')

    def isPassable(self, coord, previous=None, keys=None):
        """
        If previous not give, returns True if the terrain at coord is passable, False otherwise.
        If previous is give, returns True if the terrain at coord is passable and move from previous-->cord is legal, False otherwise.
        :type keys: ((int,int))
        :rtype : bool
        """
        if previous:
            return not self.getCost(coord, previous, keys) == float('inf') 
        else:
            return self.isCellTraversable(coord, keys)

    def nearestPassable(self, current=None):
        """Tests coordinate passed in as current to make sure it's passable. If not,
           conducts breadth first search to identify nearest passable and returns that.
           If no coord passed in, generates one randomly."""
        if not current:
            return self.generateCoord()
        if not self.cellWithinBoundaries(current):
            current = self.placeOnMap(current);
        q = deque()  # fastest append/pop
        L = []  # ordinary list
        closed = set()  # fastest membership test
        closed.add(current)
        while not self.isPassable(current):
            L = self.getAllAdjacents(current)
            for adj in L:
                if adj not in closed and adj not in q:
                    q.append(adj)
            current = q.popleft()
            closed.add(current)
        return current

    def generateCoord(self):
        """Randomly generate new coordinate and return nearest passable."""
        x = randint(10, self.width - 10)  # allow 10 pixel margin, so not right at edge
        y = randint(10, self.height - 10)
        return self.nearestPassable((x, y))
        
    def placeOnMap(self, coord):
        """Return coordinate moved onto map"""
        col, row = coord
        if col > self.width:
            col = self.width - 1
        elif col < 0:
            col = 0
        if row > self.height:
            row = self.height - 1
        elif row < 0:
            row = 0
        return (col, row)

    def getAllAdjacents(self, position):
        """Return all adjacent coordinates - horizontal, vertical and diagonal -  whether
           or not they are passable, and regardless of config file setting for DIAGONAL."""
        (col, row) = position
        L = []
        for x in range(col - 1, col + 2):
            for y in range(row - 1, row + 2):
                if (x == col and y == row) or x < 0 or y < 0 or x > self.width - 1 or \
                        y > self.height - 1:
                    continue
                L.append((x, y))
        return L

    def _getDiagAdjacents(self, position):
        """Internal. Returns 8 neighbours. Called as getAdjacents() when DIAGONAL set to True"""
        (col, row) = position
        col = int(col)
        row = int(row)
        L = [(x, y)
             for x in range(col - 1, col + 2)
             for y in range(row - 1, row + 2)
             if not ((x == col and y == row) or x < 0 or y < 0 or x > self.width - 1 or y > self.height - 1)
             # if (x,y) is not position and self.cellWithinBoundaries((x,y)) 
        ]
        return L

    def _getNonDiagAdjacents(self, position):
        """Internal. Returns 4 neighbours. Called as getAdjacents() when DIAGONAL set to False"""
        (col, row) = position
        L = []
        if col > 0:
            L.append((col - 1, row))
        if col + 1 < self.width - 1:
            L.append((col + 1, row))
        if row > 0:
            L.append((col, row - 1))
        if row + 1 < self.height - 1:
            L.append((col, row + 1))
        return L

    def _euclid(self, current, goal):
        """Internal. Called as getH() if HEURISTIC set to 'euclid'"""
        xlen = current[0] - goal[0]
        ylen = current[1] - goal[1]
        return sqrt(xlen * xlen + ylen * ylen)

    def _manhattan(self, current, goal):
        """Internal. Called as getH() if HEURISTIC set to 'manhattan'"""
        return fabs((current[0] - goal[0]) + (current[1] - goal[1]))
        
    def _octile(self, current, goal):
        """Internal. Called as getH() if HEURISTIC set to 'octile'"""
        xlen = fabs(current[0] - goal[0])
        ylen = fabs(current[1] - goal[1])
        return max(xlen, ylen) + self.OCT_CONST * min(xlen, ylen)

    def getMixedCost(self, terrain1, terrain2, diag=False):
        """
        Returns cost from mixedmatrix based on terrain types passed in.
        Default returns cost of straight move. For diagonal move, set diag to True.
        If terrain doesn't exist, returns None.
        :type terrain1: str
        :type terrain2: str
        :type diag: bool
        :rtype: float
        """
        return self.mixedmatrix.get((terrain1, terrain2, diag))
        

    def _readMap(self, mappath, costpath):
        """
        Internal. Generates matrix. Initialises info and populates costs.
        Called from init. Sets matrix to None if map load fails.
        Differentiates between uniform and non-uniform cost based on length
        map header.
        """
        self.info = {}
        try:
            with open(mappath, "r") as f:
                # print("Parsing")
                for line in f:
                    if line.strip() == 'map':
                        break
                    parsed = line.split()
                    key = parsed[0]
                    if key == "type":
                        continue
                    elif parsed[1] == "+inf":
                        self.info[key] = float("inf")
                    elif key == "key":  # this if the map includes keys/objects
                        i = 3
                        key_location = (int(parsed[1]), int(parsed[2]))
                        self.key_and_doors[key_location] = []
                        while i + 1 < len(parsed):
                            self.key_and_doors[key_location].append((int(parsed[i]), int(parsed[i + 1])))
                            i += 2
                        # print(self.key_and_doors)
                    else:   
                        self.info[key] = int(parsed[1]) 
                # generate matrix - using 'zip' so that it reads back (col, row)
                _matrix = [list(line.rstrip()) for line in f]
                self.matrix = [list(x) for x in zip(*_matrix)]  # make it a list so can change it
                # self.matrix = list(zip(*_matrix))

                # if cost file specified, read it and overwrite whatever cost is so far
                if costpath:
                    with open(costpath, "r") as f:
                        for line in f:
                            parsed = line.split()
                            key = parsed[0]
                            if parsed[1] == "+inf":
                                self.info[key] = float("inf")
                            else:   
                                self.info[key] = int(parsed[1]) 
                
                # replace terrain types with costs obtained from map (if any), then guess whether it is uniform or not
                self.setCostCells(self.info)  # set cost as per read from the map file above
                if len(set(self.costs.values()).difference(set([float('inf')]))) == 1:
#                 if all(self.costs[x] == self.costs['G'] for x in ('W', '.', 'S')):
                    self.uniform = True
                else:
                    self.uniform = False

            # now we have everything, build mixedmatrix
            #TODO: fix this to respect the input cost model
            for x in self.costs:
                for y in self.costs:
                    # handle water from non-water for uniform cost maps
                    if self.uniform and y == "W" and not x == "W":
                        self.mixedmatrix[x, y, True] = float('inf')
                        self.mixedmatrix[x, y, False] = float('inf')
                    else:
                        # diagonal moves
                        self.mixedmatrix[x, y, True] = (self.costs[y]) * self.SQRT2
                        # straight moves
                        self.mixedmatrix[x, y, False] = self.costs[y]

        except EnvironmentError:
            print("Error parsing map file")
            self.matrix = None

    def isMapped(self, node):
        """ returns True if node is on map """
        return 0 <= node[0] < self.width and 0 <= node[1] < self.height
        
    def setPoints(self, terrain, pointlist):
        for each in pointlist:
            self.setCell(terrain, each)
            
    def setCell(self, char, position):
        """Modifies matrix. Ignores if char is invalid terrain type or position is off-map"""
        if char in self.costs and self.cellWithinBoundaries(position):
            x, y = position
            self.matrix[x][y] = char

    def validator(self, path):
        """Checks validity of path and returns cost. Invalid path returns infinity.
        List comprehension calls getCost() on every pair of coordinates. 
        Uses current cost model and assumes path is ordered from start to goal.
        :type path: list of tuples [(col, row),(col, row), ...] 
        :rtype: float
        """
        return sum([self.getCost(path[i],path[i-1]) for i in range(len(path))[1:]])
