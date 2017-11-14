from heapq import heappush, heappop
import  p4_utils as p4               #contains colours and constants
from time import clock as timer
import math
INF = float('inf')
PRECISION = 800 #large constant used with minimal_2 to preserve precision

class GrAgent(object):
    opt_costs = {}  #dictionary by coord, stores opt_cost from start to goal coord
    
    def __init__(self, **kwargs):
        #Formula 0 = complex, 1 = simple, 2 = minimal_1, 3 = minimal_2
        if kwargs:
            formula = kwargs['formula']
            self.costdif = (self.cd_complex, self.cd_simple, self.cd_minimal_1, self.cd_minimal_2)[formula]
        self.model = None
        self.start = None
        
    def setCostDif(self, index):
        self.costdif = (self.cd_complex, self.cd_simple, self.cd_minimal_1, self.cd_minimal_2)[index]
    
    def reset(self):
        self.helper = Helper()
        self.helper.reset()
        GrAgent.opt_costs.clear()
        
    def setNewOptcost(self,start,goal):
        print "setting new optcost"
        optc_sg = self.getOptcSG(start, goal)
        GrAgent.opt_costs[goal] = optc_sg

    def getProbs(self, model, start, goals, obs):
        self.model = model
        if not start == self.start:
            print start, self.start
            self.reset()
            self.start=start
        for goal in goals:
            clockstart = timer()  # start timer
            #print "Getting costdif...",
            costdif = self.costdif(start,goal.coord,obs)
            clockstop = timer()  # stop timer
            goal.costdif = costdif
            goal.p = self.calcProbability(costdif)
            goal.t = clockstop - clockstart
            #print costdif
            
        #likelihoods.append( posterior_probs )
        sum = 0.0
        for goal in goals: sum += goal.p
        # P(G|O)
        for goal in goals:
            try :
                goal.p = round(goal.p/sum,3)
                #probs.append( [ h.Probability_O/sum for h in hyps ] )
            except ZeroDivisionError :
                print "All P(O|G) = 0!!!"
                #sys.exit(1)
                goal.p = 1/len(goals)
        return goals
 
    #PRIVATE METHODS
    def cd_complex(self, start, goal, obs):
        #calculate and return costdif based on complex formula
        optc_sog = self.getOptcSOG(start, goal, obs)
        optcNot_sog = self.helper.getCostNobs(self.model, start, goal, obs)
        costdif = optc_sog - optcNot_sog
        return round(costdif,5)
        
    def cd_simple(self, start, goal, obs):
        #calculate and return costdif based on simple formula
        try:
            optc_sg = GrAgent.opt_costs[goal]
        except:
            self.setNewOptcost(start, goal)
            optc_sg = GrAgent.opt_costs[goal]
        optc_sog = self.getOptcSOG(start, goal, obs)
        costdif = optc_sog - optc_sg
        return round(costdif,5)
               
    def cd_minimal_1(self, start, goal, obs):
        #calculate and return costdif based on minimal formula
        try:
            optc_sg = GrAgent.opt_costs[goal]
        except:
            self.setNewOptcost(start,goal)
            optc_sg = GrAgent.opt_costs[goal]
        optc_ng = round(self.helper.getCost(self.model, obs[len(obs)-1], goal), 5)
        costdif = optc_ng - optc_sg
        return round(costdif,5)  
        
    def cd_minimal_2(self, start, goal, obs):
        #calculate and return costdif based on minimal formula2
        try:
            optc_sg = GrAgent.opt_costs[goal]
        except:
            self.setNewOptcost(start,goal)
            optc_sg = GrAgent.opt_costs[goal]
        optc_ng = round(self.helper.getCost(self.model, obs[len(obs)-1], goal), 5)
        costdif = optc_ng - optc_sg
        return round(costdif + PRECISION,5)  
        
    def getOptcSOG(self, start, goal, obs):
        #calculate and return cost from start to goal through observations
        optc_so = self.helper.getCost(self.model, start, obs[0])
        cost_o = 0
        for i in range(len(obs)-1):
            cost_o = cost_o + self.helper.getCost(self.model, obs[i], obs[i+1])
        optc_og = self.helper.getCost(self.model, obs[len(obs)-1], goal)
        total = optc_so + cost_o + optc_og
            
        return total

    def getOptcSG(self, start, goal):
        #first time, calculate opt_cost to goal; thereafter retrieve and return from dic
        try:
            return GrAgent.opt_costs[goal]
        except:
            GrAgent.opt_costs[goal] = round(self.helper.getCost(self.model, start, goal), 5)  
            return GrAgent.opt_costs[goal]          
     
    def calcProbability(self, delta):
        #Comments and code from Ramirez & Geffner:
        
        # P(O|G) / P( \neg O | G) = exp { -beta Delta(G,O) }
	    # Delta(G,O) = cost(G,O) - cost(G,\neg O)
        beta = 0.1
        likelihood_ratio = math.exp(-beta*(delta))
        # P(O|G) =  exp { -beta Delta(G,O) } / 1 + exp { -beta Delta(G,O) }
        #prob_O = likelihood_ratio / ( 1.0 + likelihood_ratio ) 
        #prob_not_O = 1.0 - prob_O	
        return likelihood_ratio / ( 1.0 + likelihood_ratio ) 
        

	
class Helper(object):
    #Modified path-planner to calculate opt costs for all formulas
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
        
