# Copyright (C) 2015 Peta Masters and Sebastian Sardina
#
# This file is part of "P4-Simulator" package.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

# 20/4/15: modified for dynamic changes

import os
import imp
import signal
import ast
import p4_utils as p4  # sets constants
import importlib

# NOTE: info output has been commented out - cannot output to CLI during
# automated testing - expected return values are csv results only.
# If output required, add after settings have been loaded
# so can check automated testing not in progress (as elsewhere).
if p4.TIMER == "time":
    from time import time as timer
    # print("using other timer")
else:
    from time import clock as timer
    # print("using internal timer")

# For speed, rather than if/else statements at runtime, load
# whichever class is appropriate to os but call them by same alias.
if os.name == 'posix':
    # from time import time as timer
    from p4_utils import Timeout
else:
    # from time import clock as timer
    from p4_utils import WinTimeout as Timeout

from time import sleep
from p4_model import LogicalMap


class SimController(object):
    """
    Controls the simulator. Handles all the business logic, inc search.
    Maintains interface between Agent and GUI.
    """

    def __init__(self, cfgfile, args):
        """
        Constructor. Sets defaults, then reads config file - which creates logical map,
        then either performs search and reports result to command line or imports view
        module, initialises GUI, and waits.

        :type cfgfile: string
        :type args: dict[string,object]
        """
        if args.get("AUTO") is False:
            print("Initialising SimController")
        # set defaults
        self.lmap = None    # Ref to LogicalMap object
        self.gui = None     # Ref to Gui object
        self.agent = None   # Ref to Agent object
        self.gen = None     # Ref to step generator
        self.current = None  # current search coordinates
        self.pathcost, self.pathsteps, self.pathtime = 0, 0, 0
        self.timeremaining = float('inf')
        self.timeout = float('inf')

        self.path = set()  # set of all coordinates displayed as part of path
        self.fullsearchflag = False  # set to True if map is populated with extra coords
        self.coordsets = None  # sets of coordinates that will need to be reset

        self.cfg = args     # Default params as modified via CLI
        self.gotscript = False
        self.script = {}  # Allows for dynamic changes
        
        #we distinguish 3 modes - config file, CLI or auto (i.e. CLI but on a loop).
        if cfgfile is not None:
            self.readConfig()
            self.gen = self.stepGenerator(self.cfg["START"], self.cfg["GOAL"])
        else:
            try:
                #self.cfg = args
                self.setStart(ast.literal_eval(self.cfg.get("START")))
                self.setGoal(ast.literal_eval(self.cfg.get("GOAL")))            
                self.cfg["DEADLINE"] = float(self.cfg.get("DEADLINE"))
                self.cfg["FREE_TIME"] = float(self.cfg.get("FREE_TIME"))
                
                self.processMap()       #imports map to model may return BadMap exception
                self.processPrefs()     #passes heuristic and deadline preferences to model
                self.resetVars()

                self.initAgent()
                
            except p4.BadAgentException:
                print("Bad Agent. Irrecoverable error. Terminating...")
                raise SystemExit()
                
            except p4.BadMapException:
                print("Bad Map. Irrecoverable error. Terminating...")
                raise SystemExit()

            except:
                print("Irrecoverable error. Terminating...")
                import traceback
                print(traceback.format_exc())
                raise SystemExit()
        
        if self.cfg.get("GUI"):
            self.initGui()
        else:
            self.search()
            
    def processMap(self):
        #may throw BadMapException
        try:
            mappath = os.path.join("..", "maps", self.cfg["MAP_FILE"])
            if not os.path.exists(mappath):
                mappath = None
            # create logical map object
            self.lmap = LogicalMap(mappath)
            # add mapref to cfg dictionary so all settings can be passed to Agent in one go
            self.cfg["MAPREF"] = self.lmap
        except:
            raise p4.BadMapException()
            
    def processPrefs(self):
        # pass preferences to lmap
        self.lmap.setHeuristic(self.cfg.get("HEURISTIC"))
        self.lmap.setDiagonal(self.cfg.get("DIAGONAL"))
        
    def initAgent(self):
        # initialise agent - may throw BadAgentException
        try:
            agentfile = "agents/" + self.cfg.get("AGENT_FILE")
            self.loadAgent(agentfile)
        except:
            raise p4.BadAgentException()

    def readConfig(self):
        """
        Reads config file into self.cfg dictionary. Initialises
        lmap, agent,  and gen. May be called from p4_view (menu option).

        :type filename: string
        """
        filename = self.cfg.get("CFG_FILE")
            
        if self.cfg.get("AUTO") is False:
            print("Reading " + filename)
        try:
            # track previous MAP_FILE setting - map only needs to be redrawn if it's changed
            oldmap = self.cfg.get("MAP_FILE")   #may be None
            execfile(filename, self.cfg)
            
            if self.cfg.get("AUTO") is False:
                #display setings
                print "\n"
                for a,b in self.cfg.iteritems():
                    #exclude unprintables
                    if a is not "__builtins__" and a is not "MAPREF":
                        print str(a) + ":" + str(b) + " ",
                print "\n"
            
            self.processMap()
            self.processPrefs()
            self.setStart(self.cfg.get("START"))
            self.setGoal(self.cfg.get("GOAL"))
            
            self.initAgent()

            if self.gui is not None:    #reset has been called from the gui
                self.gui.setLmap(self.lmap)
                if not oldmap == self.cfg.get("MAP_FILE"):
                    self.gui.vmap.drawMap(self.lmap)
                self.hdlReset()  #includes resetVars
            else:
                self.resetVars()  # no attempt to update GUI
            
                
        except p4.BadMapException:
            self.updateStatus("Unable to load map: " + self.cfg.get("MAP_FILE"))
        except p4.BadAgentException:
            self.updateStatus("Unable to load agent: " + self.cfg.get("AGENT_FILE"))
        except:
            # unexpected error
            import traceback
            print(traceback.format_exc())
            self.updateStatus("Problem reading config file!")
            

    def resetVars(self):
        """Resets tracked variables based on current self.cfg settings"""
        self.pathcost, self.pathsteps, self.pathtime = 0, 0, 0
        self.path.clear()
        self.timeremaining = self.cfg.get("DEADLINE")
        # if a DEADLINE has been set, timeout will occur at 2* that DEADLINE if Agent
        # fails to return result (Unix only)
        if not self.timeremaining:
            self.timeremaining = float("inf")
            self.timeout = float("inf")
        else:
            self.timeout = self.timeremaining * 2
        self.current = self.cfg["START"]
        
        #check for script file and load if it exists
        if self.cfg["DYNAMIC"] is True:
            self.loadScript()   #sets self.gotscript
        elif self.gotscript is True:
            self.gotscript = False

        # reconfigure generator based on current config
        self.gen = self.stepGenerator(self.cfg["START"], self.cfg["GOAL"])

    def initGui(self):
        """Imports view module, initialises Gui, and waits """
        from p4_view import Gui
        self.updateStatus("Launching GUI...")
        self.gui = Gui(self, self.lmap)
        self.gui.setStart(self.cfg["START"])
        self.gui.setGoal(self.cfg["GOAL"])
        self.updateStatus("OK")
        self.gui.mainloop()

    def search(self):
        """Performs command line search by calls to generator """
        self.updateStatus("Searching...")
        nextstep = self.cfg["START"]

        # keep generating next steps as long as goal not in goal & enough time
        while not nextstep == self.cfg["GOAL"] and self.timeremaining:
            try:
                # Don't set signal for infinite time
                if self.timeout < float('inf'):
                    with Timeout(self.timeout):  # call under SIGNAL
                        # print "timeout: ", self.timeout
                            nextstep = self.gen.next()
                else:
                    nextstep = self.gen.next()  # call with no SIGNAL
            except Timeout.Timeout:
                #import traceback
                self.timeremaining = 0
                self.updateStatus("Timed Out!")
            except:
                self.updateStatus("Agent returned " + str(nextstep))
                break
        self.hdlStop()

    def stepGenerator(self, current, target):
        """
        Generator referenced by self.gen
        Passes mapref, currentpos, goal, timeremaining to Agent
        Retrieves and yields next step on search path.

        Note: gen maintains state for supplied coordinates but updates pathCost,
        pathSteps, pathTime and timeremaining.

        p4 uses this same generator for command line and GUI search.

        :param current: Current position.
        :type current: (int, int)
        :param target: Target position.
        :type target: (int,int)
        :rtype : (int,int)
        """
        
        while True:
            target = self.cfg["GOAL"]
            if self.gotscript:
                if self.pathsteps in self.tc:
                    terrain, topleft, botright = self.tc.get(self.pathsteps)
                    pointlist = p4.getBlock(topleft,botright)
                    #change logical map
                    self.lmap.setPoints(terrain, pointlist)
                    #change in gui, if running
                    try:
                        self.gui.clearPoints(pointlist)
                    except:
                        pass
                if self.pathsteps in self.gc:
                    target = self.lmap.nearestPassable(self.gc.get(self.pathsteps))
                    self.setGoal(target)
                if self.pathsteps in self.ac:
                    newpos = p4.addVectors(current,self.ac.get(self.pathsteps))
                    current = self.lmap.nearestPassable(newpos)
                    yield newpos    #scripted move is not costed or counted
            try:
                clockstart = timer()  # start timer
                nextreturn = self.agent.getNext(self.lmap, current, target, self.timeremaining)
                clockend = timer()
            except:
                raise p4.BadAgentException()
               
            #If the step involved no reasoning (took less than FREE_TIME) do not count its time
            if ((clockend - clockstart) < self.cfg.get("FREE_TIME")):
                steptime = 0
            else:
                steptime = (clockend - clockstart)
            previous = current

            # Agent may have returned single step or step plus sets of coords and colors.
            # Try/except distinguishes between them
            try:
                x = nextreturn[1][0]  # fails if nextreturn is coord only
                current, configsets = nextreturn
            except TypeError:
                current = nextreturn
            finally:
                self.pathsteps += 1
                self.pathtime += steptime
                self.timeremaining -= steptime
                
                # We now consider every door open. In fact, we are just computing the final path cost, we are not
                # searching for it. So is reasonable to assume that I have all the keys along the path.
                allkeys = [k for k in self.lmap.key_and_doors.keys()]
                cost = self.lmap.getCost(current, previous, allkeys)
                #self.pathcost += self.lmap.getCost(current, previous, allkeys)
                if not self.lmap.isAdjacent(current,previous):
                    cost = float('inf')
                self.pathcost += cost
                # agent has made illegal move:
                if cost == float('inf'):
                    if not self.cfg.get("AUTO"):
                        print("infinity at step " + str(self.pathsteps-1) + ", " + str(current) + ":" + str(self.lmap.getCost(current)))

            yield nextreturn

    # BUTTON HANDLERS
    def hdlReset(self, msg="OK"):
        """Button handler. Clears map, resets gui and calls setVars"""
        if self.gotscript:
            self.lmap = LogicalMap("../maps/" + self.cfg["MAP_FILE"])
            self.gui.setLmap(self.lmap)
            self.gui.vmap.drawMap(self.lmap)
            self.cfg["MAPREF"] = self.lmap
            self.cfg["GOAL"] = self.gc["ORIGIN"]
            
        else:
            # clear map
            self.gui.vmap.clear(self.path, self.lmap)
            if self.fullsearchflag:
                self.updateStatus("Redrawing map")
                self.updateStatus("Please wait...", False)
                for (a, b) in self.coordsets:
                    self.gui.vmap.clear(a, self.lmap)
                self.fullsearchflag = False
                self.updateStatus("", False)
            # resize and reposition
            self.gui.resetPos()
            self.gui.resetZoom()
        # reset vars
        self.resetVars()
        self.agent.reset(**self.cfg)

        self.gui.setStart(self.cfg["START"])
        self.gui.setGoal(self.cfg["GOAL"])

        self.updateStatus(msg)
        self.updateStatus("", False)  # clears statusbar R

    def hdlStop(self):
        """Button handler. Displays totals."""
        if self.cfg.get("AUTO"):
            print(str(self.pathcost) + ";" + \
                  str(self.pathsteps) + ";" + \
                  '{0:.5g}'.format(self.pathtime) + ";" + \
                  '{0:.5g}'.format(self.timeremaining))
        else:
            if isinstance((self.pathcost),int):
                totalcost = str(self.pathcost)
            else:
                totalcost = '{0:.2f}'.format(self.pathcost)
            message = "Total Cost : " + totalcost + \
                      " | Total Steps : " + str(self.pathsteps) + \
                      " | Time Remaining : " + '{0:.5f}'.format(self.timeremaining) + \
                      " | Total Time : " + '{0:.5f}'.format(self.pathtime)

            self.updateStatus(message)

    def hdlStep(self):
        """Button handler. Performs one step for GUI Step or Search.

           Checks for goal, calls gen to get next step from agent, displays step on map,
           and updates status bar. If "SPEED" set, inserts delay.

           Note: delay occurs whether called as single step or within
           continuous search; with step, the delay is unnoticeable because of the time
           taken to click the button again."""
        if not self.current == self.cfg["GOAL"] and self.timeremaining:

            try:
                if self.timeout < float('inf'):
                    with Timeout(self.timeout):  # call under SIGNAL
                        nextreturn = self.gen.next()
                else:
                    nextreturn = self.gen.next()  # call with no SIGNAL
            except Timeout.Timeout:
                if self.timeremaining < 0:
                    self.timeremaining = 0
                    self.updateStatus("Timeout!", False)
                else:
                    self.updateStatus("No path found", False)
                self.hdlStop()
            except:
                self.updateStatus("Agent returned " + str(nextreturn), False)
                self.hdlStop()
            else:
                # try/except to distinguish single step from step plus sets of coordinates
                try:  # process sets of coordinates
                    x = nextreturn[1][0]
                except TypeError:
                    nextstep = nextreturn
                else:
                    #something to draw
                    #self.updateStatus("Drawing...", False)
                    nextstep, coordsets = nextreturn
                    for coordset in coordsets:
                        if coordset[1] == 'reset':
                            self.gui.vmap.clear(coordset[0], self.lmap)
                        else:
                            self.gui.vmap.drawSet(coordset[0], coordset[1])
                    self.gui.setStart(self.cfg["START"])
                    self.gui.setGoal(self.cfg["GOAL"])
                    self.fullsearchflag = True
                    self.coordsets = coordsets
                    #self.updateStatus("Plotting path...", False)
                finally:  # paint path
                    self.gui.vmap.drawSet(self.path, "blue")
                    self.gui.vmap.drawPoint(nextstep, "white")
                    self.current = nextstep
                    self.path.add(nextstep)
                    if isinstance((self.pathcost),int):
                        currcost = str(self.pathcost)
                    else:
                        currcost = '{0:.2f}'.format(self.pathcost)
                    message = str(nextstep) + " | Cost : " + currcost + \
                        " | Steps : " + str(self.pathsteps)
                    if self.cfg.get("DEADLINE"):
                        message += " | Time remaining: " + \
                                   '{0:.5f}'.format(self.timeremaining)
                    self.updateStatus(message)
                    sleep(self.cfg.get("SPEED"))  # delay, if any
                    

    # MENU HANDLERS
    def loadMap(self, mapfile):
        """
        Menu handler: File - Open Map. Loads map based on openfiledialog in
        view. Creates new LogicalMap object and resets based on config

        :type mapfile: string
        """
        try:
            self.updateStatus("Loading map...")
            self.lmap = LogicalMap(mapfile)

            # pass new LogicalMap references to Gui and MapCanvas (vmap)
            self.gui.setLmap(self.lmap)
            self.gui.vmap.drawMap(self.lmap)
        
        except:
            self.updateStatus("Unable to load map: " + mapfile)
            
        else:        
            self.cfg["MAPREF"] = self.lmap
            self.processPrefs()
            # generate random start and goal coordinates
            x = y = None
            while x == y:  # make sure start != goal
                x = self.lmap.generateCoord()
                y = self.lmap.generateCoord()
            self.cfg["START"] = x
            self.cfg["GOAL"] = y

            self.cfg["MAP_FILE"] = os.path.basename(mapfile)
            msg = "Loaded " + self.cfg["MAP_FILE"]
            self.hdlReset(msg)

            
    def setStart(self, start=None):
        """Menu handler: Search - Reset Start"""
        if start:
            self.cfg["START"] = start
        else:
            self.cfg["START"] = self.lmap.generateCoord()
        if self.gui is not None:
            self.hdlReset("Start moved to " + str(self.cfg["START"]))

    def setGoal(self, goal=None):
        """Menu handler: Search - Reset Goal"""
        if goal:
            self.cfg["GOAL"] = goal
        else:
            self.cfg["GOAL"] = self.lmap.generateCoord()
        if self.gui is not None:
            self.gui.clearGoal()
            self.gui.setGoal(self.cfg["GOAL"])
            self.updateStatus("Goal moved to " + str(self.cfg["GOAL"]))
            #self.hdlReset("Goal moved to " + str(self.cfg["GOAL"]))

    def loadAgent(self, agentpath):
        """Menu handler: Search - Load Agent. Loads agent based on openfiledialog in
           view. Also called from readConfig()"""
        try:
            agentfile = os.path.basename(agentpath)
            if agentfile[-3:] == ".py":  # strip extension from agentfile, if present
                agentfile = agentfile[:-3]
            else:
                agentpath = agentpath + ".py"  # add extension to agentpath, if absent
            # load or reload module
            agentmod = imp.load_source(agentfile, agentpath)
            # create Agent and pass in current config settings
            self.agent = agentmod.Agent()
            self.agent.reset(**self.cfg)

            self.updateStatus("Initialised " + agentfile)
            
        except:
            self.updateStatus("Unable to load " + agentfile)
            import traceback
            print(traceback.format_exc())
        else:
            self.cfg["AGENT_FILE"] = agentfile


    def areWeThereYet(self):
        """Returns True/False."""
        return self.current == self.cfg["GOAL"]

    def outOfTime(self):
        """Returns True/False."""
        return (self.timeremaining <= 0)

    def getSettings(self):
        """Getter. Returns current config dictionary"""
        return self.cfg

    def updateStatus(self, msg, left=True):
        """Updates GUI status bar with supplied message.
           If left = False, outputs to right. Outputs to left by default."""
        if self.gui is not None :
            if left:
                self.gui.setStatusL(msg)  # fails if no gui
            else:
                self.gui.setStatusR(msg)
        else:
            # no gui - print to terminal
            if not self.cfg.get("AUTO"):
                print(msg)

    def loadScript(self):
        try:
            execfile('script.py', self.script)
            self.gc = self.script.get("GOAL_CHANGE")
            self.gc["ORIGIN"] = self.cfg["GOAL"]    #save in case of reset
            self.tc = self.script.get("TERRAIN_CHANGE")
            self.ac = self.script.get("AGENT_CHANGE")
            self.gotscript = True
            self.updateStatus("Loaded script")
        except: #we don't care why it failed
            self.updateStatus("Failed to load script.py")
            

if __name__ == '__main__':
    print("To run the P4 Simulator, type 'python p4.py' " + \
          "at the command line and press <Enter>")

