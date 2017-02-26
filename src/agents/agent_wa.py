from heapq import heappush, heappop, heapify
from time import time

INF = float('inf')
X_POS = 0
Y_POS = 1

class Agent(object):
    """Weighted A* using Pohl's original definition - when weight = 1, algorithm returns greedy; when weight = 0, algorithm = Dijkstra"""
    def __init__(self, **kwargs):
        if kwargs: 
            self.w = kwargs['weight']                  # 0 <= self.w <= 1 
        else:
            self.w = 1
            
    def setWeight(self, weight):
        self.w = weight
        
    def reset(self, **kwargs):
        self.start = None           # starting point
        self.goal = None            # goal
        self.mapref = None          # logic map
        self.parents = {}           # parents
        self.stepgen = self.step_gen()
        
    def getPath(self, model, start, goal):
        self.reset()
        return self.astar(model, start, goal)
        
    def getCost(self, model, start, goal):
        self.reset()
        return self.astar(model, start, goal, True)
        
    def getNext(self, mapref, current, goal, timeremaining):
        self.start = current
        self.goal = goal
        self.mapref = mapref
        return next(self.stepgen)

    def step_gen(self):
        path = self.astar(self.mapref, self.start, self.goal)
        for step in path:
            yield step

    def reconstruct_path(self, current, parents):
        path = []
        while current in parents:
            path.insert(0, current)
            current = parents[current]
        return path

    def astar(self, mapref, start, goal, flag = False):
        open = []
        self.open_dict = {}
        heapify(open)
        closed = {}
        self.g_score = {start: 0}
        heappush(open, (0, start, 0))
        self.open_dict[start] = None
        g_child = 0
        
        # avoid "."
        getH = mapref.getH
        getAdj = mapref.getAdjacents
        getCost = mapref.getCost
        closed_has = closed.has_key
        open_has = self.open_dict.has_key
        getCell = mapref.getCell
        matrix = mapref.matrix
        
        # Check if goal has already been reached
        if start == goal:
            return start
            
        # Astar
        while(open):
            # pop first in queue
            current = heappop(open)[1]
            del self.open_dict[current]
            if current == goal:
                if flag:    #just need cost, not path
                    return self.g_score[current]
                return self.reconstruct_path(current, self.parents)
            # Add to closed list
            closed[current] = None
            # Get and check all adjacent nodes from current position
            for n in getAdj(current):
                # Check if it is an obstacle
                if matrix[n[X_POS]][n[Y_POS]] == '@':
                    continue
                # Check if it is passable
                g_child = getCost(n, current)
                if g_child == INF:
                    continue
                g = self.g_score[current] + g_child
                # Is it in closed list with a smaller value?
                if closed_has(n): #and g >= self.g_score[n]:
                    continue
                if not open_has(n) or g < self.g_score[n]:
                    # Assign current as the parent of n
                    self.parents[n] = current
                    # Update g score
                    self.g_score[n] = g
                    if not open_has(n):
                        #f(n) = (1 - w) * g(n) + w * h(n) - g increases as h decreases and vice versa
                        try:
                            f = (1 - self.w) * g + self.w * getH(goal, n)
                        except: 
                            print self.w, g, getH(goal, n)
                            f = (1 - self.w) * g + self.w * getH(goal, n)
                        heappush(open, (f, n))
                        self.open_dict[n] = None
        #path not found
        return None

