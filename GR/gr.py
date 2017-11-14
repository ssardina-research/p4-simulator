import p4_utils as p4
import csv, os, imp, random
from p4_model import LogicalMap
from time import clock as timer
from random import randint

if os.name == 'posix':
    # from time import time as timer
    from p4_utils import Timeout
else:
    # from time import clock as timer
    from p4_utils import WinTimeout as Timeout

COMPLEX = 0
SIMPLE = 1
MINIMAL1 = 2
MINIMAL2 = 3

OPTIMAL = 0
SUBOPTIMAL = 0.6
GREEDY = 1

SPARSE = 20
MEDIUM = 50
DENSE = 80

PREFIX = 0
RANDOM = 1

OBS_AGENT = "agent_wa"
#OBS_AGENT = "agent_rta"
#GR_AGENT = "gr_agent_ramirez"
GR_AGENT = "gr_agent"

MAP_PATH = "../maps/gr/"
MAX_GOALS = 7
TIME_OUT = 180  #3 minutes

"""GR is hard-coded to run a batch from a modified scen file. It uses weighted A* to generate 3 sets of observations and from each of those creates 6 problems to solve - one with each of 20%, 40%, 60% obs delivered as a continuous path prefix or a randomised sequence."""
class GR(object):
    def __init__(self, prob_file, sol_file = None):
        self.infile = prob_file
        if sol_file:
            self.outfile = sol_file
        else:
            self.outfile = self.infile + ".csv"
            
        #initialise agents    
        try:
            temp = imp.load_source(OBS_AGENT, './agents/'+OBS_AGENT+'.py')
            self.obs_agent = temp.Agent()
            temp = imp.load_source(GR_AGENT, './agents/'+GR_AGENT+'.py')
            self.gr_agent = temp.GrAgent()

        except Exception, e:
            print "Expecting agent name only. "
            self.fatalError(e)
            
        self.map = None
        print "Initialised GR."
                    
    def runBatch(self, quality, density=None, distribution=None):
        """
        Read problems, generate observed path and run getProbabities()
        Requires agents to exist
        """
        print "Running batch..."
        qualities = (OPTIMAL, SUBOPTIMAL, GREEDY)
        if density:
            densities = (density,)
            distributions = (distribution,)
        else:
            densities = (SPARSE, MEDIUM, DENSE) 
            distributions = (PREFIX,RANDOM)
        obs_sets = (self.prefix, self.random)
        #edit directly to restrict to one formula only
        formulas = (COMPLEX, SIMPLE, MINIMAL1, MINIMAL2)
        
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
                    # self.model.setDiagonal(False)   #
                    self.map = map
                                  
                #generate paths, get probabilities * 6 and write to csv
                for density in densities:
                    for distribution in distributions:
                        fullpath = self.getFullPath(start, goals[realgoal].coord, quality)
                        obs_set = obs_sets[distribution]
                        obs = obs_set(fullpath, density)
                        print numgoals + 1, len(goals)
                        for formula in formulas:
                            print "formula " + str(formula) + ":"
                            self.gr_agent.setCostDif(formula)
                            try:
                                with Timeout(TIME_OUT):
                                    clockstart = timer()  # start timer - getting results for all 3 goals
                                    goal_results = self.gr_agent.getProbs(self.model, start, goals, obs)  #populate goals
                                    clockend = timer()  # start timer - getting results for all 3 goals
                            except Timeout.Timeout:
                                print "Timeout error"
                                goal_results = goals    
                                clockend = clockstart + 180
                                for goal in goal_results:
                                    goal.setTime("TIMED OUT")
                            writearray = [map, start, optcost, "Q_"+str(quality), "D_"+str(density), ("P","R")[distribution], formula]
                            count = 0
                            print numgoals + 1, len(goal_results)
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
        try:
            self.obs_agent.setWeight(weight)
        except:
            pass
        return self.obs_agent.getPath(self.model, start, goal)
   
    def outputLine(self, outfile, writearray, goals):   
        try:
            if not os.path.isfile(outfile):        
                headerlist = ["map", "start", "optcost", "quality", "density", "distribution", "formula"]
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
        self.target = False
    def setProb(self, prob):
        self.p = prob
    def setTime(self, timing):
        self.t = timing
    def getData(self):
        return [(self.coord[0], self.coord[1]), self.costdif, self.p, self.t]
    def setTarget(self, target):
        self.target = target
    def isTarget(self):
        return target
        
if __name__ == '__main__':

    recog = GR( "../maps/gr/rooms.GR", "./tests/rooms_gdy.csv")
    recog.runBatch(GREEDY)
