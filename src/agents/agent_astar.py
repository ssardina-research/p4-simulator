# Copyright (C) 2015-17 Peta Masters and Sebastian Sardina
#

from heapq import heappush, heappop
from agents.agent import AgentP4
import  p4_utils as p4               #contains colours and constants
#from twisted.python.util import println

class Agent(AgentP4):
    """Uses A* algorithm to calculate and return open list, closed list, and path
    
    The main function is get_next() to yield the next step, possibly with working info
    """
    def __init__(self,**kwargs):
        self.reset()

    def reset(self):
        """Initialises step generator"""
        self.stepgen = None
        self.goal = None
        self.nextmove = None
        self.mapref = None
        self.draw = False
        self.closedlist = {}
        self.openlist = []

    def get_working_lists(self):
        # self.openlist contains prio-queue of nodes (f, g, coord, parent)
        # First, unpack the prio-queue via *self.openlist to get a flat sequence of nodes
        # Then zip all those nodes to get four components: all the f's, all the g's, all the coord, and all the parent
        # finally we keep all the coord ([2]) (in Python 3 zip() gives iterator, so we need to convert to list)

        coord_open_list = []
        if self.openlist:
            coord_open_list = list(zip(*self.openlist))[2], p4.COLOR_OPENLIST

        return ( (coord_open_list, p4.COLOR_OPENLIST), (self.closedlist, p4.COLOR_CLOSELIST))

    def get_next(self, mapref, current, goal, timeremaining):
        """Provide the next step to be performed by the agent towards goal.

        A step is just a coordinate (x, y) to move to or
        a tuple ((x,y), ((list1,col1), (list2,col2), (list3,col3))) where
        with the second part being working lists (open, closed, path) to draw with their colors
        """

        # map, goal or expected location have changed? re-do the generation planner
        if not mapref == self.mapref or not goal == self.goal or not current == self.nextmove:
            self.reset()
            self.goal = goal
            self.mapref = mapref
            self.stepgen = self._gen(current)   # reset generator

        return next(self.stepgen)

    def _gen(self, current):
        """ Step generator. Yields next step to go from current location to goal location.

           On first entry, calls planpath to do a full search and stores the path,
           thereafter yields the next step in the path.
        """
        self._planpath(self.mapref, current, self.goal)   # perform search from current to goal, store path in self.path

        if not self.path:   # no path to destination goal!
            yield None

        # Extract first move
        self.nextmove = self.path[0]

        if self.draw:
            # first move goes with open, closed and path list for drawing, then yield each move one-by-one
            yield self.nextmove, ((self.closedlist.keys(), p4.COLOR_CLOSELIST), \
               (zip(*self.openlist)[2], p4.COLOR_OPENLIST), (self.path, p4.COLOR_PATH))

        # yield reverse_path[0]
        for move in self.path:
            self.nextmove = move
            yield self.nextmove

    def _planpath(self, mapref, start, goal, all=False):
        """ Performs A* from start coord to goal coord on map mapref """
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
                # yes! reconstruct the path form start to goal
                self._reconstruct_path(current, start)
                return

            # expand current node by getting all successors and adding them to open list
            successors = (mapref.getAdjacents(current))
            for next_coord in successors:
                next_g = current_g + mapref.getCost(next_coord, current)
                next_f = next_g + mapref.getH(next_coord, goal)
                next_node = (next_f, next_g, next_coord, current)
                if next_coord not in self.closedlist:
                    heappush(self.openlist, next_node)
        self.path = None   # no path has been found

    def _reconstruct_path(self, current, start):
        """
           Reconstruct the path from start to current (generally current = goal)
        """
        self.path = [current]
        while not current == start:
            current = self.closedlist[current][p4.P_POS]
            self.path = [current, *self.path]   # we unpack the current path to put it at the end
        return


assert issubclass (Agent, AgentP4)
assert isinstance (Agent(), AgentP4)