from time import clock as timer
import math

class GrAgent(object):
    opt_costs = {}  #dictionary by coord, stores opt_cost from start to goal coord
    
    def __init__(self, **kwargs):
        #Formula 0 = complex, 1 = simple, 2 = minimal
        if kwargs:
            formula = kwargs['formula']
            self.costdif = (self.cd_complex, self.cd_simple, self.cd_minimal)[formula]
        self.model = None
        self.helper = None
        self.start = None
        
    def setCostDif(self, index):
        self.costdif = (self.cd_complex, self.cd_simple, self.cd_minimal)[index]
    
    def reset(self):
        GrAgent.opt_costs.clear()
        
    def setHelper(self, helper):
        self.helper = helper

    def getProbs(self, model, start, goals, obs):
        self.model = model
        if not start == self.start:
            self.reset()
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
        #print "Optcost with obs:" + str(optc_sog)
        optcNot_sog = self.helper.getCostNobs(self.model, start, goal, obs)
        #print "Optcost without obs:" + str(optcNot_sog)
        costdif = optc_sog - optcNot_sog
        return costdif
        
    def cd_simple(self, start, goal, obs):
        #calculate and return costdif based on simple formula
        optc_sog = self.getOptcSOG(start, goal, obs)
        optc_sg = self.getOptcSG(start, goal)
        #print "Optcost_sg:" + str(optc_sg)
        costdif = optc_sog - optc_sg
        return costdif
               
    def cd_minimal(self, start, goal, obs):
        #calculate and return costdif based on minimal formula
        optc_sg = self.getOptcSG(start, goal)
        optc_ng = round(self.helper.getCost(self.model, obs[len(obs)-1], goal), 5)
        costdif = optc_ng - optc_sg
        return costdif + 200        #TODO - HOW MANY TO ADD OK SO LONG AS SAME ACROSS ALL GOALS?  
        
    def getOptcSOG(self, start, goal, obs):
        #calulate and return cost from start to goal through observations
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
        # P(O|G) / P( \neg O | G) = exp { -beta Delta(G,O) }
	    # Delta(G,O) = cost(G,O) - cost(G,\neg O)
        beta = 1
        likelihood_ratio = math.exp(-beta*(delta))
        # P(O|G) =  exp { -beta Delta(G,O) } / 1 + exp { -beta Delta(G,O) }
        #prob_O = likelihood_ratio / ( 1.0 + likelihood_ratio ) 
        #prob_not_O = 1.0 - prob_O	
        return likelihood_ratio / ( 1.0 + likelihood_ratio ) 
        

	
        
