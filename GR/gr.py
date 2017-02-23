"""
GR is hard-coded to run a batch from a modified scen file. 
It uses weighted A* to generate 3 sets of observations and from 
each of those creates 6 problems to solve 
- one with each of 3 densities delivered 
as a continuous path prefix or a randomised sequence.
"""
#############################
#Settings
COMPLEX = 0
SIMPLE = 1
MINIMAL = 2

OPTIMAL = 0
SUBOPTIMAL = 0.6
GREEDY = 1

SPARSE = 20
MEDIUM = 50
DENSE = 80

PREFIX = 0
RANDOM = 1

OBS_AGENT = "agent_wa"
GR_AGENT = "gr_agent_ramirez"
HELPER_AGENT = "helper"

MAP_PATH = "../maps/gr/"
AGENT_PATH = "./agents/"
MAX_GOALS = 7
TIME_OUT = 180  #seconds
#############################

import csv, os, imp, random
from p4_model import LogicalMap
from time import clock as timer
from random import randint

#timeout only implemented for Unix - WinTimeout is a dummy function
if os.name == 'posix':
    from p4_utils import Timeout
else:
    from p4_utils import WinTimeout as Timeout

class GR(object):
    def __init__(self, prob_file, sol_file = None):
        self.infile = prob_file
        if sol_file:
            self.outfile = sol_file
        else:
            self.outfile = self.infile + ".csv"
            
        #initialise agents            
        try:
            temp = imp.load_source(OBS_AGENT, AGENT_PATH+OBS_AGENT+'.py')
            self.obs_agent = temp.Agent()

            temp = imp.load_source(GR_AGENT, AGENT_PATH+GR_AGENT+'.py')
            self.gr_agent = temp.GrAgent()

            temp = imp.load_source(HELPER_AGENT, AGENT_PATH+HELPER_AGENT+'.py')
            self.gr_agent.setHelper(temp.Agent())
        except Exception, e:
            print "Expecting agent name only. "
            self.fatalError(e)
            
        self.map = None
        print "Initialised GR."
                    
    def runBatch(self):
        """
        Read problems, generate observed path and run getProbabities()
        Requires agents to exist
        """
        print "Running batch..."
        
        qualities = (OPTIMAL, SUBOPTIMAL, GREEDY)
        densities = (SPARSE, MEDIUM, DENSE)
        obs_sets = (self.prefix, self.random)
        formulas = (COMPLEX, SIMPLE, MINIMAL)       
        
        with open(self.infile, 'r') as f:
            reader = csv.reader(f)
            next(reader)                                            #skip header row
            counter = 1
            for problem in reader:
                print "Processing problem " + str(counter)
                counter = counter + 1
                map, optcost = problem[:2]                          #first two elements
                optcost = float(optcost)
                problem_ints = [int(i) for i in problem[2:]]        #remaining elements, all integers
                numgoals, scol, srow, gcol, grow = problem_ints[:5] 
                start = (scol, srow)
                goals = [GoalObj('goal0', gcol, grow)]

                #parse extra goals
                for i in range(numgoals):
                    goals.append(GoalObj('goal'+str(i+1), problem_ints[5+i*2], problem_ints[6+i*2]))

                realgoal = 0
                
                if not self.map == map:
                    self.model = LogicalMap(MAP_PATH + map)
                    self.map = map
                                  
                #one loop to generate paths, extract obs, get probabilities, and write to csv
                for quality in qualities:
                    fullpath = self.getFullPath(start, goals[0].coord, quality)
                    for density in densities:
                        distribution = -1       #initialise counter so increments to 0
                        for obs_set in obs_sets:
                            distribution = distribution + 1
                            print "QDD", str(quality), str(density), str(distribution)
                            obs = obs_set(fullpath, density)
                            goalset = []
                            for formula in formulas:
                                self.gr_agent.setCostDif(formula)
                                try:
                                    with Timeout(TIME_OUT):
                                        clockstart = timer()  
                                        goal_results = self.gr_agent.getProbs(self.model, start, goals, obs)  #populate goals
                                        clockend = timer() 
                                except Timeout.Timeout:
                                    print "Timeout error"
                                    goal_results = goals    
                                    clockend = clockstart + TIME_OUT
                                    for goal in goal_results:
                                        goal.setTime("TIMED OUT")
   

                                writearray = [map, start, optcost, "Q_"+str(quality), "D_"+str(density), ("P","R")[distribution], str(numgoals+1), formula]
                                count = 0
                                for goal in goal_results:
                                    count = count + 1
                                    writearray.extend(goal.getData())
                                for i in range(MAX_GOALS - count):  #align columns
                                    writearray.extend(["","","",""])
                                writearray.append(clockend-clockstart)
                                self.outputLine(self.outfile, writearray, goals)                                 
                 
        print "Results written to " + self.outfile
                 
    def getFullPath(self, start, goal, weight):
        self.obs_agent.reset()
        #might use agent other than weighted A*
        try:
            self.obs_agent.setWeight(weight)
        except:
            pass
        return self.obs_agent.getPath(self.model, start, goal)
   
    def outputLine(self, outfile, writearray, goals):   
        try:
            #First time, write headings
            if not os.path.isfile(outfile):        
                headerlist = ["map", "start", "optcost", "quality", "density", "distribution", "#goals", "formula"]
                for counter in range(MAX_GOALS):
                    headerlist.extend(["goal"+ str(counter), "costdif", "probability", "calctime"])
                headerlist.append("total_time")
                with open(outfile, 'wb') as f:
                    csvout = csv.writer(f)
                    csvout.writerow(headerlist)
                    
            with open(outfile, 'ab') as f:
                csvout = csv.writer(f)
                csvout.writerow(writearray)
        except Exception, e:
            self.fatalError(e)
            
    def random(self, path, percent):
        #extract randomised sequence
        total_obs = len(path)
        num_obs = total_obs * percent / 100
        not_less_than = 1               #skip start
        not_more_than = total_obs - 1   #range skips last anyway
        indices = random.sample(range(not_less_than, not_more_than), num_obs)
        indices.sort()
        obs = [path[i] for i in indices]
        return obs
        
    def prefix(self, path, percent):
        #returns continuous path prefix
        total_obs = len(path)
        num_obs = total_obs * percent / 100
        return path[:num_obs]

    def fatalError(self, errstr):
        print str(errstr) + "\n"
        import sys, traceback
        print(traceback.format_exc())
        sys.exit(1)

class GoalObj(object):
    def __init__(self, id, x, y):
        self.id = id
        self.coord = (x, y)
        self.costdif = None
        self.p = None
        self.t = None
    def getData(self):
        return [(self.coord[0], self.coord[1]), self.costdif, self.p, self.t]


if __name__ == '__main__':
    recog = GR( "../maps/gr/sample.GR", "sample.csv")
    recog.runBatch()

