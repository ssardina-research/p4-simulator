# Copyright (C) 2013-17 Peta Masters and Sebastian Sardina
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

import os
import imp
import importlib
import signal
import ast
import p4_utils as p4  # sets constants
import traceback
import csv
import copy
import logging


if p4.TIMER == "time":
    from time import time as timer

    logging.info("Using other timer")
else:
    from time import clock as timer

    logging.info("Using internal timer")

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
        logging.info("Initialising SimController")
        # set defaults
        self.lmap = None  # Ref to LogicalMap object
        self.gui = None  # Ref to Gui object
        self.agent = None  # Ref to Agent object
        self.gen = None  # Ref to step generator
        self.current = None  # current search coordinates
        self.pathcost, self.pathsteps, self.pathtime = 0, 0, 0
        self.timeremaining = float('inf')
        self.timeout = float('inf')

        self.path = set()  # set of all coordinates displayed as part of path
        self.keptpath = None
        self.fullsearchflag = False  # set to True if map is populated with extra coords
        self.coordsets = None  # sets of coordinates that will need to be reset

        self.cfg = args  # Default params as modified via CLI
        self.gotscript = False
        self.script = {}  # Allows for dynamic changes

        # we distinguish 3 modes - config file, CLI or batch
        if cfgfile is not None:
            self.readConfig()
            self.gen = self.stepGenerator(self.cfg["START"], self.cfg["GOAL"])
        elif self.cfg["BATCH"] is not None:
            try:
                self.runBatch(*self.cfg["BATCH"])
                logging.info("\nBatch process completed. Results written to " + self.cfg["BATCH"][1] + ".\n")
            except Exception as e:
                logging.warning(
                    "\nAn error has occurred. Batch results may be incomplete. Here is the exception: \n {}".format(e))
            finally:
                raise SystemExit()
        else:
            try:
                self.setStart(ast.literal_eval(self.cfg.get("START")))
                self.setGoal(ast.literal_eval(self.cfg.get("GOAL")))

                self.initAgent()
                self.processMap()  # imports map to model may return BadMap exception
                self.processPrefs()  # passes heuristic and deadline preferences to model
                self.resetVars()

            except p4.BadAgentException:
                logging.error("Bad Agent. Irrecoverable error. Terminating...")
                raise SystemExit()

            except p4.BadMapException:
                logging.error("Bad Map. Irrecoverable error. Terminating...")
                raise SystemExit()

            except:
                logging.error("Irrecoverable error. Terminating...")
                logging.error("Trace-back: \n {}".format(traceback.format_exc()))
                raise SystemExit()

        if self.cfg.get("GUI"):
            self.initGui()
        else:
            self.search()

    def processMap(self):
        # may throw BadMapException
        try:
            mappath = os.path.join("..", "maps", self.cfg["MAP_FILE"])
            if not os.path.exists(mappath):
                mappath = None
                logging.info("Map file not found: loading default.")
                self.cfg["MAP_FILE"] = None

            # if cost file exists, get file 
            costpath = None
            if self.cfg["COST_FILE"] and os.path.exists(self.cfg["COST_FILE"]):
                costpath = os.path.join(self.cfg["COST_FILE"])
            # create logical map object
            self.lmap = LogicalMap(mappath, costpath)
        except:
            raise p4.BadMapException()

    def processPrefs(self):
        self.cfg["DEADLINE"] = float(self.cfg.get("DEADLINE"))
        self.cfg["FREE_TIME"] = float(self.cfg.get("FREE_TIME"))
        # pass preferences to lmap
        self.lmap.setCostModel(self.cfg.get("COST_MODEL"))
        self.lmap.setDiagonal(self.cfg.get("DIAGONAL"))
        self.lmap.setHeuristic(self.cfg.get("HEURISTIC"))

        if self.cfg["PREPROCESS"]:
            try:
                self.agent.preprocess(self.lmap)
            except AttributeError:
                logging.warning("Agent doesn't support pre-processing.")
            except:
                # some other problem
                logging.error("Pre-processing failed.")
                logging.error("Trace-back: \n {}".format(traceback.format_exc()))

    def initAgent(self):
        # initialise agent - may throw BadAgentException
        try:
            dirname_agent = os.path.dirname(self.cfg.get("AGENT_FILE"))
            basename_agent = os.path.basename(self.cfg.get("AGENT_FILE"))

            if not dirname_agent:
                # if no directory is specified, assume ../maps/
                dirname_agent = 'agents/'
            else:
                dirname_agent = dirname_agent + '/'

            agentfile = dirname_agent + basename_agent
            logging.info("Agent to be used: {}".format(agentfile))
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

        logging.info("Reading configuration file **{}**".format(filename))
        try:
            # track previous MAP_FILE setting - map only needs to be redrawn if it's changed
            oldmap = self.cfg.get("MAP_FILE")  # may be None
            execfile(filename, self.cfg)

            # display setings
            out = '\n'
            for a, b in self.cfg.iteritems():
                # exclude unprintables
                if a is not "__builtins__" and a is not "MAPREF":
                    out = "{} \t {}: {}\n".format(out, a, b)
            # logging.info
            logging.info("Options read from configuration file: {}".format(out))

            self.initAgent()
            self.processMap()
            logging.info("Starting agent pre-processing...")
            self.processPrefs()
            self.setStart(self.cfg.get("START"))
            self.setGoal(self.cfg.get("GOAL"))

            if self.gui is not None:  # reset has been called from the gui
                self.gui.setLmap(self.lmap)
                if not oldmap == self.cfg.get("MAP_FILE"):
                    self.gui.vmap.drawMap(self.lmap)
                self.hdlReset()  # includes resetVars
            else:
                self.resetVars()  # no attempt to update GUI


        except p4.BadMapException:
            self.updateStatus("Unable to load map: " + self.cfg.get("MAP_FILE"))
        except p4.BadAgentException:
            self.updateStatus("Unable to load agent: " + self.cfg.get("AGENT_FILE"))
        except:
            # unexpected error
            logging.error("Trace-back: \n {}".format(traceback.format_exc()))
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

        # check for script file and load if it exists
        if self.cfg["DYNAMIC"] is True:
            self.loadScript()  # sets self.gotscript
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
        while not self.cfg["GOAL"] == nextstep and self.timeremaining:
            try:
                # Don't set signal for infinite time
                if self.timeout < float('inf'):
                    with Timeout(self.timeout):  # call under SIGNAL
                        nextstep = self._get_coordinate(self.gen.next())
                else:
                    nextstep = self._get_coordinate(self.gen.next())  # call with no SIGNAL
            except Timeout.Timeout:
                self.timeremaining = 0
                self.updateStatus("Timed Out!")
            except:
                self.updateStatus("Agent returned " + str(nextstep))
                logging.error("Trace-back: \n {}".format(traceback.format_exc()))
                raise SystemExit()
                break

        return self.hdlStop()

    # just keep the first argument of a nextstep, and drop any possible argument for drawing lists
    def _get_coordinate(self, nextstep):
        # nexstep = (x,y) or nextstep = ((x,y), (list1,list2,list3))
        if isinstance(nextstep[1], (list, tuple)):
            return nextstep[0]
        else:
            return nextstep

    # just keep the second argument of a nextstep (the list for drawings), and drop the coordinate
    def _get_drawing_lists(self, nextstep):
        # nexstep = (x,y) or nextstep = ((x,y), (list1,list2,list3))
        # is the second part of nextstep (list1,list2,list3)? If so, just keep the coordinate argument
        if isinstance(nextstep[1], (list, tuple)):
            return nextstep[1]
        else:
            return None

    def keepPath(self):
        # Pins current path to map
        self.keptpath = copy.deepcopy(self.path)
        self.gui.vmap.drawSet(self.keptpath, "orange")

    def losePath(self):
        self.gui.vmap.clear(self.keptpath, self.lmap)
        self.gui.vmap.drawSet(self.path, "blue")
        self.keptpath = None

    def showWorkings(self):
        # Used by gets drawing lists, if getWorkings() is supported by agent
        try:
            coordsets = self.agent.getWorkings()
        except:
            self.updateStatus("No working sets available.", False)
        else:
            for coordset in coordsets:
                if coordset[1] == 'reset':
                    self.gui.vmap.clear(coordset[0], self.lmap)
                else:
                    self.gui.vmap.drawSet(coordset[0], coordset[1])
            # redraw start and goal on top
            self.gui.setStart(self.cfg["START"])
            self.gui.setGoal(self.cfg["GOAL"])
            self.coordsets = coordsets
            self.fullsearchflag = True

    def hideWorkings(self):
        if self.fullsearchflag:
            for (a, b) in self.coordsets:
                took_action = True
                self.gui.vmap.clear(a, self.lmap)
            if self.keptpath:
                self.gui.vmap.drawSet(self.keptpath, "orange")
            self.gui.vmap.drawSet(self.path, "blue")
            self.gui.setStart(self.cfg["START"])
            self.gui.setGoal(self.cfg["GOAL"])
            self.gui.cancelWorkings()
        self.fullsearchflag = False

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
                    pointlist = p4.getBlock(topleft, botright)
                    # change logical map
                    self.lmap.setPoints(terrain, pointlist)
                    # change in gui, if running
                    try:
                        self.gui.clearPoints(pointlist)
                    except:
                        pass
                if self.pathsteps in self.gc:
                    target = self.lmap.nearestPassable(self.gc.get(self.pathsteps))
                    self.setGoal(target)
                if self.pathsteps in self.ac:
                    newpos = p4.addVectors(current, self.ac.get(self.pathsteps))
                    current = self.lmap.nearestPassable(newpos)
                    yield newpos  # scripted move is not costed or counted
            try:
                clockstart = timer()  # start timer
                nextreturn = self.agent.getNext(self.lmap, current, target, self.timeremaining)
                logging.debug(nextreturn)
                clockend = timer()
            except:
                raise p4.BadAgentException()

            # Only time first step unless operating in 'realtime' mode. If this is realtime, and the step involved no reasoning (took less than FREE_TIME) do not count its time
            if ((not self.cfg.get("REALTIME") and self.pathtime) or (
                        (clockend - clockstart) < self.cfg.get("FREE_TIME"))):
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
                # self.pathcost += self.lmap.getCost(current, previous, allkeys)
                if not self.lmap.isAdjacent(current, previous):
                    cost = float('inf')
                # agent has made illegal move:
                if cost == float('inf'):
                    self.updateStatus("Illegal move at " + str(current) + ":" + str(self.lmap.getCost(current)), False)
                    if self.cfg["STRICT"]:
                        current = previous
                        nextreturn = previous
                        self.pathsteps -= 1
                        cost = 0
                self.pathcost += cost
            yield nextreturn

    # BUTTON HANDLERS
    def hdlReset(self, msg="OK"):
        """Button handler. Clears map, resets gui and calls setVars"""
        if self.gotscript:
            self.lmap = LogicalMap("../maps/" + self.cfg["MAP_FILE"])
            self.gui.setLmap(self.lmap)
            self.gui.vmap.drawMap(self.lmap)
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
        self.agent.reset()

        self.gui.setStart(self.cfg["START"])
        self.gui.setGoal(self.cfg["GOAL"])
        if self.keptpath:
            self.gui.vmap.drawSet(self.keptpath, "orange")
        self.gui.cancelWorkings()
        self.updateStatus(msg)
        self.updateStatus("", False)  # clears statusbar R

    def hdlStop(self):
        """Button handler. Displays totals."""
        if isinstance((self.pathcost), int):
            totalcost = str(self.pathcost)
        else:
            totalcost = '{0:.4f}'.format(self.pathcost)

        message = "Total Cost : " + totalcost + \
                  " | Total Steps : " + str(self.pathsteps) + \
                  " | Time Remaining : " + str(self.timeremaining) + \
                  " | Total Time : " + str(self.pathtime)

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
            else:  # try/except/else...
                # does nextreturn include a list of coordinates to draw?
                if isinstance(nextreturn[1], (list, tuple)):
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
                    self.updateStatus("Plotting path...", False)
                else:
                    # nextreturn just includes the next coordinate, no drawing data
                    nextstep = nextreturn

                    # Paint path
                self.gui.vmap.drawSet(self.path, "blue")
                self.gui.vmap.drawPoint(nextstep, "white")
                self.current = nextstep
                self.path.add(nextstep)
                if isinstance((self.pathcost), int):
                    currcost = str(self.pathcost)
                else:
                    currcost = '{0:.2f}'.format(self.pathcost)
                message = str(nextstep) + " | Cost : " + currcost + \
                          " | Steps : " + str(self.pathsteps)
                if self.cfg.get("DEADLINE"):
                    message += " | Time remaining: " + \
                               str(self.timeremaining)
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
            self.gui.clearStart()
            self.gui.setStart(self.cfg["START"])
            self.updateStatus("Start moved to " + str(self.cfg["START"]))
            # TODO check search not in progress before resetting generator.
            self.gen = self.stepGenerator(self.cfg["START"], self.cfg["GOAL"])

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
            self.agent.reset()

            self.updateStatus("Initialised " + agentfile)
        except:
            self.updateStatus("Unable to load " + agentfile)
            logging.error("Trace-back: \n {}".format(traceback.format_exc()))
            raise
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
        if self.gui is not None:
            if left:
                self.gui.setStatusL(msg)  # fails if no gui
            else:
                self.gui.setStatusR(msg)
        else:
            # no gui - print to terminal
            logging.info("STATUS REPORTING (no GUI): {}".format(msg))

    def loadScript(self):
        try:
            execfile('script.py', self.script)
            self.gc = self.script.get("GOAL_CHANGE")
            self.gc["ORIGIN"] = self.cfg["GOAL"]  # save in case of reset
            self.tc = self.script.get("TERRAIN_CHANGE")
            self.ac = self.script.get("AGENT_CHANGE")
            self.gotscript = True
            self.updateStatus("Loaded script")
        except:  # we don't care why it failed
            self.updateStatus("Failed to load script.py")

    def runBatch(self, infile, outfile, reps=1):
        # assumes MAP_FILE, AGENT_FILE set in self.cfg
        # initialise map and agent
        logging.info("\nRunning batch...")
        times = []
        reps = int(reps)
        self.processMap()
        self.initAgent()
        self.processPrefs()
        # open scenario file and read into problems list
        scenario = open(infile)
        problems = [line.strip().split() for line in scenario if len(line) > 20]
        scenario.close

        # If csv file doesn't exist, create and write header, then close
        if not os.path.isfile(outfile):
            with open(outfile, 'wb') as csvfile:
                fcsv = csv.writer(csvfile, delimiter=',',
                                  quotechar='|', quoting=csv.QUOTE_MINIMAL)
                fcsv.writerow(['agent', 'no', 'map', 'startx', 'starty', 'goalx', 'goaly', 'optimum', 'actual', 'steps',
                               'time_taken', 'quality'])
        # Open existing csv file, process each problem and append results     
        with open(outfile, 'ab') as csvfile:
            fcsv = csv.writer(csvfile, delimiter=',',
                              quotechar='|', quoting=csv.QUOTE_MINIMAL)
            count = 0
            for problem in problems:
                count += 1
                skip, mappath, size1, size2, scol, srow, gcol, grow, optimum = problem
                logging.info(
                    "\n ========> Running problem {}: from ({},{}) to ({},{}) - Optimal: {}".format(count, scol, srow,
                                                                                                    gcol, grow,
                                                                                                    optimum))
                pathname, map = os.path.split(mappath)
                self.cfg["START"] = (int(scol), int(srow))
                self.cfg["GOAL"] = (int(gcol), int(grow))

                times = []
                for i in xrange(reps):
                    try:
                        self.agent.reset()
                        self.resetVars()
                        output = self.search()
                        actual_cost, steps, time, inf = str.split(output, ';')
                        times.append(float(time))
                        actual_cost = round(float(actual_cost), 2)  # to compare with movingai costs
                    except:
                        pass
                if len(times) > 0:
                    time = sum(times) / reps  # calculate average

                    try:
                        quality = float(optimum) / float(actual_cost)
                    except ZeroDivisionError:
                        quality = 0
                    fcsv.writerow(
                        [self.cfg["AGENT_FILE"], count, map, str(scol), srow, gcol, grow, optimum, actual_cost, steps,
                         time, quality])


if __name__ == '__main__':
    logging.info("To run the P4 Simulator, type 'python p4.py' at the command line and press <Enter>")
