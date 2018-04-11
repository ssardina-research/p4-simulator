"""strategy 1"""
from heapq import heappush, heappop, heapify
from time import time
from math import fabs, sqrt 
import sys, traceback 

import deceptor as d

OCT_CONST = 0.414
INF = float('inf')
X_POS = 0
Y_POS = 1

class Agent(object):
    """Simple dpp strategies return path that maximises LDP"""
    def __init__(self, **kwargs):
        pass
            
    def reset(self, **kwargs):
        self.stepgen = self.step_gen()
        
    def setGoals(self, poss_goals):
        #Called by controller to pass in poss goals
        self.poss_goals = poss_goals
        
    def getNext(self, mapref, current, goal, timeremaining):
        #print "received request"
        self.start = current 
        self.real_goal = goal
        self.mapref = mapref
        return next(self.stepgen)

    def step_gen(self):
        #print "running generator"
        all_goal_coords = [self.real_goal] + self.poss_goals
        goal_obs = d.generateGoalObs(self.mapref, self.start, all_goal_coords)
        rmp, argmin = d.rmp(self.mapref, self.start, goal_obs)
        path1 = self.mapref.optPath(self.start,argmin.coord)
        path2 = self.mapref.optPath(argmin.coord, self.real_goal)
        path = path1[1:] + path2[1:]

        for step in path:
            yield step        
        
    def getFullPath(self, mapref, start, goal, poss_goals, heatmap):
        #returns cost and path
        all_goal_coords = [goal] + poss_goals
        goal_obs = d.generateGoalObs(mapref, start, all_goal_coords)
        rmp, argmin = d.rmp(mapref, start, goal_obs)
        cost1, path1 = mapref.optPath(start,argmin.coord, 2)
        cost2, path2  = mapref.optPath(argmin.coord, goal, 2)

        return cost1 + cost2, path1[1:] + path2[1:]
        
