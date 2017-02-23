from heapq import heappush, heappop
import  p4_utils as p4               #contains colours and constants
INF = float('inf')

class Agent(object):

    def __init__(self,**kwargs):
        print "loaded new helper"
        
    def reset(self, **kwargs):     
        self.open = None
        self.closed = None
        self.open_has = None
        
    def getCost(self, model, start, goal):
        self.reset()
        return self._planpath(model, start, goal, True)
        
    def getCostNobs(self, model, start, goal, obs):
        if start == goal:
            return 0    
        open = []
        closed = {}
        openlist = {}
        open_has = openlist.has_key
        getH = model.getH
        getAdj = model.getAdjacents
        getCost = model.getCost
        last_ob = len(obs) - 1
        
        if obs[0] == start:
            ob_counter = 1
        else:
            ob_counter = 0
            
        #node = (f, g, coord, ob_counter) - parent not needed (path not reconstructed)
        heappush(open, (getH(start, goal), 0, start, ob_counter)) #initialise open list with start node
        openlist[(start,ob_counter)] = None
        while open:
            node = heappop(open)
            current_f, current_g, current_coord, next_ob = node
            if (current_coord, next_ob) in closed or current_g == INF:
                continue 
            closed[(current_coord, next_ob)] = None  #maintained as lookup, no value needed
            
            # goal reached?
            if current_coord == goal:
                return current_g

            # expand current node by getting all successors and adding them to open list
            adjacents = (getAdj(current_coord))
            for a in adjacents:
                if a == obs[next_ob]: 
                    adj_ob = next_ob + 1
                    if adj_ob == last_ob:
                        continue            #we've seen all obs in sequence, so node is no good
                else:
                    adj_ob = next_ob
                if (a, adj_ob) in closed:
                    continue
                if not open_has((a, adj_ob)):
                    adjg = current_g + getCost(a, current_coord)
                    adjf = adjg + getH(a, goal)
                    adjnode = (adjf, adjg, a, adj_ob)
                    heappush(open, adjnode) 
                    openlist[(adjnode,adj_ob)] = None
                    
        print "path not found"            
        return INF 
        
    def _planpath(self, mapref, start, goal, cost_only = False):
        if start == goal:
            if cost_only:
                return 0
            else:
                return goal    
        open = []
        closed = {}
        getH = mapref.getH
        getAdj = mapref.getAdjacents
        getCost = mapref.getCost
        
        heappush(open, (getH(start, goal), 0,start,None))
        while open:
            node = heappop(open)
            current_f, current_g, coord, current_parent = node
            if coord in closed or current_g == float('inf'):
                continue 
            closed[coord] = current_parent
            
            # goal reached?
            if coord == goal:
                if cost_only:
                    return current_g
                return self._reconstruct(coord, closed)

            # expand current node by getting all successors and adding them to open list
            adjacents = (getAdj(coord))
            for a in adjacents:
                if a not in closed:
                    adjg = current_g + getCost(a, coord)
                    adjf = adjg + getH(a, goal)
                    adjnode = (adjf, adjg, a, coord)
                    heappush(open, adjnode)
                    
        return INF #path not found

    #_reconstruct, getNext and _gen retained for testing
    def _reconstruct(self, current, closed):
        path = []
        while closed[current]:
            path.insert(0, current)
            current = closed[current]           
        return path

    def getNext(self, mapref, current, goal, timeremaining):      
        if not mapref == self.mapref or not goal == self.goal:
            self.goal = goal
            self.mapref = mapref
            self.stepgen = self._gen(current)       
        return self.stepgen.next() 

    def _gen(self, current):
        path = self._planpath(self.mapref, current, self.goal)  
        for move in path:
            yield move
