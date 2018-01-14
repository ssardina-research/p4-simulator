# Copyright (C) 2015-17 Peta Masters and Sebastian Sardina
#

from heapq import heappush, heappop
import  p4_utils as p4               #contains colours and constants
#from twisted.python.util import println

class Agent(object):
    """Uses A* algorithm to calculate and return open list, closed list, and path"""
    def __init__(self,**kwargs):
        self.stepgen = None
        self.goal = None
        self.nextmove = None
        self.mapref = None
        self.draw = False
        
    def getWorkings(self):
        return ((zip(*self.openlist)[2], p4.COL_OL), (self.closedlist, p4.COL_CL))
        
    def getNext(self, mapref, current, goal, timeremaining):
        """called by SimController, uses generator to return next step towards goal."""

        # map, goal or expected location have changed? re-do the generation planner
        
        if not mapref == self.mapref or not goal == self.goal or not current == self.nextmove:
            self.reset()
            self.goal = goal
            self.mapref = mapref
            self.stepgen = self._gen(current)
        
        return self.stepgen.next() 

    def reset(self, **kwargs):
        """Initialises step generator"""
        self.stepgen = None
        self.goal = None
        self.nextmove = None
        self.mapref = None
        self.draw = False
        self.closedlist = {}    # dictionary of expanded nodes - key=coord, data = node
        self.openlist = []      # heap as pqueue on f_val


    def _gen(self, current):
        """ Step generator. Yields next step to go from current location to goal location.

           On first entry, calls planpath to do a full search and stores the path,
           thereafter yields the next step in the path.
        """
        # print("Planning in progress....")
        self._planpath(self.mapref, current, self.goal)   # perform search from current to goal, store path in self.path
        reverse_path = list(reversed(self.path[:len(self.path)-1]))
        
        #save each step to self.nextmove to compare at getNext()
        self.nextmove = reverse_path[0]
        
        index_start = 0
        if self.draw:
            # first move goes with open, closed and path list for drawing, then yield each move one-by-one
            yield self.nextmove, ((self.closedlist.keys(), p4.COL_CL), \
               (zip(*self.openlist)[2], p4.COL_OL), (self.path, p4.COL_PP))
            index_start = 0

        for move in reverse_path[index_start:]:
            self.nextmove = move
            yield move

    def _planpath(self, mapref, start, goal, all=False):
        """ Performs A* from start to goal on map mapref """
        if start == goal:
            return []     # 0 steps, empty self.path

        self.path = []          # path as list of coordinates

        # initialise self.openlist with start node
        # node = (f, g, coord, parent)  and start node has g=0 and f = h and no parent
        heappush(self.openlist, (mapref.getH(start, goal) , 0, start, None))

        while self.openlist:
            # pop best node from open list (lowest f)
            node = heappop(self.openlist)
            current_f, current_g, current, parent = node
            if current in self.closedlist or current_g == float('inf'):
                continue # node has to be ignored: blocked or already visited

            # add node to closelist
            self.closedlist[current] = node

            # goal reached?
            if current == goal:
                # yes! so rewind using parent links from self.closedlist to get self.path
                self._reconstruct(current, start)
                return

            # expand current node by getting all successors and adding them to open list
            adjacents = (mapref.getAdjacents(current))
            for a in adjacents:
                adjg = current_g + mapref.getCost(a, current)
                adjf = adjg + mapref.getH(a, goal)
                adjnode = (adjf, adjg, a, current)
                if a not in self.closedlist:
                    heappush(self.openlist, adjnode)

    def _reconstruct(self, current, start):
        """
           Reconstruct backwards path from current to start by following parent links
        """
        self.path = [current]
        while not current == start:
            current = self.closedlist[current][p4.P_POS]
            self.path.append(current)
        return
