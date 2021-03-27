from abc import ABC, abstractmethod, abstractproperty

class AgentP4(ABC):

    def reset():
        """Reset the agent"""
    pass


    def getNext(lmap, current, target, timeremaining):
        """Return the next step of the agent"""
    pass

    # def getWorkings():
    #     """Get theworkings of the agent, if supported. Optional method
    #
    #       Could be used to return (open list, close list)
    #     """
    # pass
