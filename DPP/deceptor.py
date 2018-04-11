"""Module of routines to support deceptive path-planning. Runs with p4."""
import traceback
def generateGoalObs(model, start_coord, goal_coords):
    #goal_coords: list of coords with real goal at index 0
    #print "generating goal objects"
    gr_coord = goal_coords[0]  
    goal_obs = []
    for g in goal_coords:
        optc = model.optCost(start_coord, g)
        optr = model.optCost(g, gr_coord)
        goal_obs.append(GoalObj(g, optc, optr))

    return goal_obs
        
def rmp1(model, start, goal_obs):
    #Expects real goal ob at index 0
    min_rmp = float('inf')
    #argmin = goal_obs[0]
    start_to_realgoal = goal_obs[0].optc    #goal_obs[0] is the realgoal
    for g in goal_obs[1:]:
        rmp = (g.optr + start_to_realgoal - g.optc)/2
        if rmp < min_rmp:
            min_rmp = rmp
            argmin = g
            
    return min_rmp, argmin
    
def rmp(model, start, goal_obs):
    #Expects real goal ob at index 0
    closest = float('inf')
    #argmin = goal_obs[0]
    start_to_realgoal = goal_obs[0].optc    #goal_obs[0] is the realgoal
    for g in goal_obs[1:]:
        if g.optr < closest:
            closest = g.optr
            closest_goal = g
    rmp = (closest_goal.optr + start_to_realgoal - closest_goal.optc)/2
            
    return rmp, closest_goal
    
def findTarget(model, rmp, argmin, realgoal_coord, heatmap):
    #assumes rmp > 0 (negative rmp implies no step from start can deceive)
    cost, path = model.optPath(argmin.coord, realgoal_coord, 2)
    targetCost = cost-rmp
    current = argmin.coord
    costSoFar = 0
    next = 1
    while costSoFar < targetCost:
        costSoFar = costSoFar + model.getCost(current, path[next])
        current = path[next]
        next = next + 1
    
    while heatmap.isTruthful(path[next-1]):
        next = next -1
        
    return path[next-1]
    
def deceptile(model, target, realgoal, argminGoal, coord):
    """evaluate octile heuristic for real and argmin goals. If real<argmin, 
        increase heuristic estimate for current target."""
    targetH = model._octile(coord, target)
    realH = model._octile(coord, realgoal)
    argminH = model._octile(coord, argminGoal)
    if realH < argminH:
        targetH = targetH * 1.5
    return targetH

##############################################
class GoalObj(object):
    def __init__(self, coord, optc, optr):
        self.coord = coord
        self.optc = optc    #optcost from start
        self.optr = optr    #optcost to real goal
        
    def display(self):
        print self.id, self.coord, self.optc, self.optr, self.gm
        
class HeatMap(object):
    def __init__(self, model, goal_obs):
        self.model = model
        self.goal_obs = goal_obs
        self.truthDic = {}    #truthful node = True, deceptive = False
        self.goal = goal_obs[0]
        #self.start_to_goal = goal_obs[0].optc
        
    def costdif(self, goal_ob, node):
        #returns cost difference with second parameter known and passed in
        try:
            return round(self.model.optCost(node, goal_ob.coord) - goal_ob.optc, 3)
        except:
            print traceback.format_exc()
            print "goal_coord", goal_ob.coord
            print "node", node
        
    def isTruthful(self, node):
        real_costdif = self.costdif(self.goal, node)
        for g in self.goal_obs[1:]:
            if g.coord == node: 
                return False
            if self.costdif(g, node) <= real_costdif:
                return False    #some goal has costdif <= to real, so node is deceptive
        return True
        
    def checkNode(self, node):
        if node not in self.truthDic:
            self.truthDic[node] = self.isTruthful(node)
        return self.truthDic[node]
            
    def createHeatMap(self):
        m = self.model
        for x in range(m.width):
            for y in range(m.height):
                #print x,y
                if not self.model.getCost((x,y)) == float('inf'):
                    self.truthDic[(x,y)] = self.isTruthful((x,y))

        
        
    
if __name__ == '__main__':
    import p4_model as m
    l = m.LogicalMap("../maps/AR0044SR.map")
    a = (338,384)
    b = (110,153)
    c = (169,341)
    d = (410,424)
    s=(23,434)
    g=(324,57)
    goal_obs = generateGoalObs(l,s,(g,a,b,c,d))
    rmp, argmin = rmp(l,s,goal_obs)
    heatmap = HeatMap(l,goal_obs)
    t = findTarget(l,rmp,argmin,g, heatmap)
    #heatmap.createHeatMap()
    
        
