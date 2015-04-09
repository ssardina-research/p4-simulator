# Copyright (C) 2015 Peta Masters and Sebastian Sardina

class Agent(object):
    def __init__(self,**kwargs):
        self.clockface = ((1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1))

    def getNext(self, mapref, current, goal, timeremaining):
        """agent_right always turns right! Agents are self-policing
        so must check cell passable from current in case of corner-cutting
        or may return invalid coord."""    
        for move in self.clockface:
            candidate = (current[0]+ move[0],current[1] + move[1])
            if mapref.isPassable(candidate, current):
                break
        return candidate

    def reset(self, **kwargs):
        pass
