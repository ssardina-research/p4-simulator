"""
                                                                                                                 
"""

#############################
#Settings

DS1 = "agent_ds1"
DS2 = "agent_ds2"
DS3 = "agent_ds3"
DS4 = "agent_ds4"

MAP_PATH = "../maps/baldurs/"
AGENT_PATH = "./agents/"
MAX_GOALS = 4
#TIME_OUT = 180  #seconds
#############################

import csv, os, imp, random
from p4_model import LogicalMap
from time import clock as timer
from random import randint
import deceptor as d

#timeout only implemented for Unix - WinTimeout is a dummy function
#if os.name == 'posix':
#    from p4_utils import Timeout
#else:
#    from p4_utils import WinTimeout as Timeout
    
class DPP(object):
    def __init__(self, prob_file, sol_file = None):
        self.infile = prob_file
        if sol_file:
            self.outfile = sol_file
        else:
            self.outfile = self.infile + ".csv"
            
        #initialise agents            
        try:         
            temp = imp.load_source(DS1, AGENT_PATH+DS1+'.py')
            Agent_DS1 = temp.Agent()

            temp = imp.load_source(DS2, AGENT_PATH+DS2+'.py')
            Agent_DS2 = temp.Agent()
            
            temp = imp.load_source(DS3, AGENT_PATH+DS3+'.py')
            Agent_DS3 = temp.Agent()
            
            temp = imp.load_source(DS4, AGENT_PATH+DS4+'.py')
            Agent_DS4 = temp.Agent()

            self.strategies = (Agent_DS1, Agent_DS1, Agent_DS2, Agent_DS3, Agent_DS4)   #n.b. strategy 0 is a dummy param, replaced by Astar.
            
        except Exception, e:
            print "Expecting agent name only. "
            self.fatalError(e)
            
        self.map = None
        print "Initialised DPP."
                    
    def runBatch(self):
        """
        Read problems, generate observed path and run agents corresponding to each strategy number.
        """
        print "Running batch..."
        
        #Directly modify prior to run - e.g. limit to one quality, one density, etc.
        densities = (10,25,50,75,90,99)    #percentage of path
        #strategyNums = (0,1,2,3,4)        #strategy zero is Astar
        strategyNums = (0,)                #strategy zero is Astar       
        
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
                realgoal = (gcol, grow)
                
                possgoals = []
                for i in range(numgoals):
                    possgoals.append((problem_ints[5+i*2], problem_ints[6+i*2]))
                                
                if not self.map == map:
                    model = LogicalMap(MAP_PATH + map)
                    self.map = map
                    
                #initialise deceptor
                all_goal_coords = [realgoal] + possgoals
                goal_obs = d.generateGoalObs(model, start, all_goal_coords)
                heatmap = d.HeatMap(model, goal_obs)  
                
                #one loop to generate paths, extract obs, get probabilities, and write to csv
                for s in strategyNums:
                    print "strategy" + str(s)
                    #get path and its cost - depends on obs_agent - i.e. strat1, strat2, strat3, strat4
                    if not s:   #strategy zero (astar)
                        clockstart = timer()
                        pathcost, fullpath = model.optPath(start, realgoal, 2)
                        clockend = timer()
                        
                        """ add this code to return path up to rmp only
                        # rmp, argmin = d.rmp(model, start, goal_obs)
                        # target = pathcost-rmp
                        # prev = start
                        # cost = 0
                        # stepnum = 0
                        # while cost < target:      
                            # stepnum = stepnum + 1
                            # step = fullpath[stepnum]
                            # cost = cost + model.getCost(step, prev)
                            # prev = step
                            
                        # fullpath = fullpath[:stepnum]"""
                        
                    else:
                        clockstart = timer()
                        pathcost, fullpath = self.strategies[s].getFullPath(model, start, realgoal, possgoals, heatmap)
                        clockend = timer()
                        
                    gentime = clockend - clockstart
                    writearray = [map, start, s, pathcost, gentime]
                    for density in densities:
                        print "Density", str(density)     
                        #find node at that pos
                        density = float(density)
                        totlength = len(fullpath) - 1
                        pathpos = int(density/100*totlength)
                        #check deceptivity                      
                        stepdecept = heatmap.isTruthful(fullpath[pathpos])
                        writearray.append(stepdecept)
                    self.outputLine(self.outfile, writearray)                                 
                 
        print "Results written to " + self.outfile
   
    def outputLine(self, outfile, writearray):   
        try:
            #First time, write headings
            if not os.path.isfile(outfile):        
                headerlist = ["map", "start", "strategy", "cost", "time", "10", "25", "50", "75", "90", "99"]
                #for counter in range(MAX_GOALS):
                #headerlist.extend(["goal"+ str(counter), "costdif", "probability", "calctime"])
                #headerlist.append("total_time")
                with open(outfile, 'wb') as f:
                    csvout = csv.writer(f)
                    csvout.writerow(headerlist)
                    
            with open(outfile, 'ab') as f:
                csvout = csv.writer(f)
                csvout.writerow(writearray)
        except Exception, e:
            self.fatalError(e)
            

    def fatalError(self, errstr):
        print str(errstr) + "\n"
        import sys, traceback
        print(traceback.format_exc())
        sys.exit(1)
        
if __name__ == '__main__':
    recog = DPP( "../maps/baldurs/dpp_dataset.GR", "../maps/baldurs/dpp_dataset.rmp")
    recog.runBatch()

