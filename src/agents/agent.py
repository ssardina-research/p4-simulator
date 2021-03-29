from abc import ABC, abstractmethod, abstractproperty

class AgentP4(ABC):

    def reset():
        """Reset the agent"""
    pass

    def get_next(lmap, current, target, timeremaining):
        """Return the next step of the agent"""
        # should return either:
        #   (x, y): next step from the agent
        #  ((x,y), (list1,list2,list3)): next step plu drawing/working lists (e.g., open and closed lists)
    pass

    def get_working_lists(self):
        """Get the workings of the agent, if supported, as lists of coord to draw.

          Could be used to return (open list, close list)
        """
    pass
