# Copyright (C) 2013-21 Peta Masters and Sebastian Sardina
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
import time
from agents.agent import AgentP4
import p4_utils as p4  # sets constants
import traceback
import csv
import copy
import logging

# For speed, rather than if/else statements at runtime, load
# whichever class is appropriate to os but call them by same alias.
if os.name == 'posix':
    # from time import time as timer
    print("using posix")
    from p4_utils import Timeout
else:
    # from time import clock as timer
    from p4_utils import WinTimeout as Timeout

from p4_model import LogicalMap


class StatusBar(object):
    """
    Keeps track of the current status bar message made of several parts
    """

    def __init__(self, msg="Status bar initialized", precision=4):
        self.cost = 0
        self.curr_step = None
        self.no_steps = 0
        self.time_left = 0
        self.time_taken = 0
        self.status = msg
        self.precision = precision
        self.message = msg
        self.report_func = None

    def reset(self, msg="Status bar reset", precision=4):
        self.cost = 0
        self.curr_step = None
        self.no_steps = 0
        self.time_left = 0
        self.time_taken = 0
        self.status = msg
        self.precision = precision
        self.message = msg

    def set(self, *arg, curr_step=None, cost=None, no_steps=None, time_left=None, time_taken=None, status=None, **kargs):
        if len(arg) == 1 and isinstance(arg[0], str):
            self.message = arg[0]
        else:
            if curr_step:
                self.curr_step = curr_step
            if cost:
                self.cost = cost
            if no_steps:
                self.no_steps = no_steps
            if time_left:
                self.time_left = time_left
            if time_taken:
                self.time_taken = time_taken
            if status:
                self.status = status
            self.message = f"Cost: {self.cost:.{self.precision}f} | Steps: {self.no_steps} | Left: {self.time_left:.{self.precision}f} | Taken: {self.time_taken:.{self.precision}f}"
            if self.curr_step:
                self.message = f"{self.curr_step} | {self.message}"
        self.display(**kargs)

    def get(self):
        return self.message

    def set_report_func(self, func):
        """Sets the reporting function"""
        self.report_func = func

    def display(self, *args, **kargs):
        """Performs the display of the current status bar message"""
        self.report_func(self.get(), *args, **kargs)


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
        self.lmap: LogicalMap = None  # Ref to LogicalMap object
        # Ref to Gui object (load the module later only if used)
        self.gui = None
        self.agent: AgentP4 = None  # Ref to Agent object
        self.gen = None  # Ref to step generator
        self.current = None  # current search coordinates
        self.pathcost, self.pathsteps, self.pathtime = 0, 0, 0
        self.timeremaining = float('inf')
        self.timeout = float('inf')

        self.status_bar = StatusBar("Status bar initialized")
        self.status_bar.set_report_func(
            lambda msg: logging.info("STATUS (no GUI): {}".format(msg)))

        self.status_bar.display()
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
                logging.info(
                    "\nBatch process completed. Results written to " + self.cfg["BATCH"][1] + ".\n")
            except Exception as e:
                logging.warning(
                    "\nAn error has occurred. Batch results may be incomplete. l"
                    " the exception: \n {}".format(e))
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
                logging.error(
                    "Trace-back: \n {}".format(traceback.format_exc()))
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
                logging.error(
                    "Trace-back: \n {}".format(traceback.format_exc()))

    def initAgent(self):
        # initialise agent - may throw BadAgentException
        try:
            dirname_agent = os.path.dirname(self.cfg.get("AGENT_FILE"))
            basename_agent = os.path.basename(self.cfg.get("AGENT_FILE"))

            agentfile = os.path.join(
                dirname_agent if dirname_agent else 'agents/', basename_agent)
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
            # execfile(filename, self.cfg)
            exec(open(filename).read(), self.cfg)

            # Display settings
            out = '\n'
            for a, b in self.cfg.items():
                # exclude un-printables
                if a != "__builtins__" and a != "MAPREF":
                    out = "{} \t {}: {}\n".format(out, a, b)
            logging.info(
                "Options read from configuration file: {}".format(out))

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
            self.status_bar.set(
                f"Unable to load map: {self.cfg.get('MAP_FILE')}")
        except p4.BadAgentException:
            self.status_bar.set(
                f"Unable to load agent: {self.cfg.get('AGENT_FILE')}")
        except:
            # unexpected error
            logging.error("Trace-back: \n {}".format(traceback.format_exc()))
            self.status_bar.set("Problem reading config file!")

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
        """
        Imports view module, initialises Gui, and waits
        """
        from p4_view import Gui
        self.status_bar.set("Launching GUI...")
        self.gui = Gui(self, self.lmap)
        self.gui.setStart(self.cfg["START"])
        self.gui.setGoal(self.cfg["GOAL"])

        # register GUI status bar report function
        self.status_bar.set_report_func(
            lambda msg, **kargs: self.gui.setStatus(msg, kargs))
        self.status_bar.set("OK")

        self.gui.mainloop()  # start TK main loop

    def search(self):
        """Performs command line search by calls to generator """
        self.status_bar.set("Executing simulation...")
        next_step = self.cfg["START"]

        # keep generating next steps as long as goal not in goal & enough time
        while not self.cfg["GOAL"] == next_step and self.timeremaining:
            try:
                # Don't set signal for infinite time
                if self.timeout < float('inf'):
                    with Timeout(self.timeout):  # call under SIGNAL
                        next_step = self._get_coordinate(next(self.gen))
                else:
                    next_step = self._get_coordinate(
                        next(self.gen))  # call with no SIGNAL
            except Timeout.Timeout:
                self.timeremaining = 0
                self.status_bar.set("Timed Out!")
            except:
                self.status_bar.set(f"Agent returned {next_step}")
                logging.error(
                    "Trace-back: \n {}".format(traceback.format_exc()))
                raise SystemExit()
                break
        return self.hdlStop()  # (totalcost, pathsteps, timeremaining, pathtime)

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
            self.status_bar.set("No working sets available.", right_side=True)
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

        p4 uses this same generator for CLI and GUI search.

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
                    target = self.lmap.nearestPassable(
                        self.gc.get(self.pathsteps))
                    self.setGoal(target)
                if self.pathsteps in self.ac:
                    newpos = p4.addVectors(
                        current, self.ac.get(self.pathsteps))
                    current = self.lmap.nearestPassable(newpos)
                    yield newpos  # scripted move is not costed or counted
            try:
                clockstart = time.process_time()
                next_cell = self.agent.getNext(
                    self.lmap, current, target, self.timeremaining)  # pair (x, y) to move
                clockend = time.process_time()
                logging.debug(next_cell)
            except:
                raise p4.BadAgentException()

            # Only time first step unless operating in 'realtime' mode. If this is realtime, and the step involved no reasoning (took less than FREE_TIME) do not count its time
            if (not self.cfg.get("REALTIME") and self.pathtime) or (clockend - clockstart) < self.cfg.get("FREE_TIME"):
                steptime = 0
            else:
                steptime = (clockend - clockstart)
            previous = current

            # Agent may have returned single step or step plus sets of coords and colors.
            # Try/except distinguishes between them
            try:
                x = next_cell[1][0]  # fails if nextreturn is coord only
                current, configsets = next_cell
            except TypeError:
                current = next_cell
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
                    self.status_bar.set(
                        f"Illegal move at {current} : {self.lmap.getCost(current)}", right_side=True)
                    if self.cfg["STRICT"]:
                        current = previous
                        next_cell = previous
                        self.pathsteps -= 1
                        cost = 0
                self.pathcost += cost
            yield next_cell






    def areWeThereYet(self):
        """Returns True/False."""
        return self.current == self.cfg["GOAL"]

    def outOfTime(self):
        """Returns True/False."""
        return (self.timeremaining <= 0)

    def getSettings(self):
        """Getter. Returns current config dictionary"""
        return self.cfg

    def loadScript(self):
        try:
            # execfile('script.py', self.script)
            exec(open("./script.py").read(), self.script)

            self.gc = self.script.get("GOAL_CHANGE")
            self.gc["ORIGIN"] = self.cfg["GOAL"]  # save in case of reset
            self.tc = self.script.get("TERRAIN_CHANGE")
            self.ac = self.script.get("AGENT_CHANGE")
            self.gotscript = True
            self.status_bar.set("Loaded script")
        except:  # we don't care why it failed
            self.status_bar.set("Failed to load script.py")

    def runBatch(self, infile, outfile, reps=1):
        # assumes MAP_FILE, AGENT_FILE set in self.cfg
        # initialise map and agent
        logging.info("\nRunning batch...")
        times_taken = []
        reps = int(reps)
        self.processMap()
        self.initAgent()
        self.processPrefs()
        # open scenario file and read into problems list
        scenario = open(infile)
        problems = [line.strip().split()
                    for line in scenario if len(line) > 20]
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
            # for each problem
            for problem in problems:
                count += 1
                skip, mappath, size1, size2, scol, srow, gcol, grow, optimum = problem
                logging.info(
                    "========> Running problem {}: from ({},{}) to ({},{}) - Optimal: {}".format(count, scol, srow,
                                                                                                 gcol, grow,
                                                                                                 optimum))
                pathname, map = os.path.split(mappath)
                self.cfg["START"] = (int(scol), int(srow))
                self.cfg["GOAL"] = (int(gcol), int(grow))

                times_taken = []
                steps_taken = []
                costs_taken = []
                # run the number of repetitions specified (on the same problem)
                for i in xrange(reps):
                    try:
                        self.agent.reset()
                        self.resetVars()
                        total_cost, total_steps, time_left, time_taken = self.search()
                        times_taken.append(float(time_taken))
                        steps_taken.append(total_steps)
                        costs_taken.append(float(total_cost))
                    except:
                        pass

                time_taken = round(sum(times_taken) / reps,
                                   5)  # calculate average
                total_steps = sum(steps_taken) / reps  # calculate average
                # calculate average -  precision to compare with movingai costs
                total_cost = sum(costs_taken) / reps

                try:
                    quality = round(float(optimum) / float(total_cost), 2)
                except ZeroDivisionError:
                    quality = 0
                fcsv.writerow(
                    [self.cfg["AGENT_FILE"], count, map, str(scol), srow, gcol, grow, optimum, total_cost,
                     total_steps, time_taken, quality])


    ################################################################################
    # BUTTON HANDLERS FOR THE GUI
    ################################################################################

    def hdlReset(self, msg="OK"):
        """Button handler. Clears map, resets GUI and calls setVars"""
        if self.gotscript:
            self.lmap = LogicalMap(os.path.join(
                "../maps/", self.cfg["MAP_FILE"]))
            self.gui.setLmap(self.lmap)
            self.gui.vmap.drawMap(self.lmap)
            self.cfg["GOAL"] = self.gc["ORIGIN"]

        else:
            # clear map
            self.gui.vmap.clear(self.path, self.lmap)
            if self.fullsearchflag:
                self.status_bar.set("Redrawing map")
                self.status_bar.set("Please wait...", right_side=False)
                for (a, b) in self.coordsets:
                    self.gui.vmap.clear(a, self.lmap)
                self.fullsearchflag = False
                self.status_bar.set("", right_side=False)
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
        self.status_bar.set(msg)
        self.status_bar.set("", right_side=True)  # clears RIGHT statusbar

    def hdlStop(self):
        """Button handler. Displays totals."""
        self.status_bar.set(cost=self.pathcost, no_steps=self.pathsteps,
                            time_left=self.timeremaining, time_taken=self.pathtime)
        return (self.pathcost, self.pathsteps, self.timeremaining, self.pathtime)

    def hdlStep(self):
        """Button handler. Only used for in GUI mode.
            Performs one step for GUI Step or Search.

           Checks for goal, calls gen to get next step from agent, displays step on map,
           and updates status bar. If "SPEED" set, inserts delay.

           Note: delay occurs whether called as single step or within
           continuous search; with step, the delay is unnoticeable because of the time
           taken to click the button again."""
        if not self.current == self.cfg["GOAL"] and self.timeremaining:
            try:
                if self.timeout < float('inf'):
                    with Timeout(self.timeout):  # call under SIGNAL
                        next_return = next(self.gen)
                else:
                    next_return = next(self.gen.next)  # call with no SIGNAL
            except Timeout.Timeout:
                if self.timeremaining < 0:
                    self.timeremaining = 0
                    self.status_bar.set("Timeout!", right_side=False)
                else:
                    self.status_bar.set("No path found", right_side=False)
                self.hdlStop()
            except:
                self.status_bar.set(
                    "Agent returned exception on new step", right_side=False)
                self.hdlStop()
            else:  # try/except/else...
                # does nextreturn include a list of coordinates to draw?
                if isinstance(next_return[1], (list, tuple)):
                    next_step, coord_sets = next_return
                    for coord_set in coord_sets:
                        if coord_set[1] == 'reset':
                            self.gui.vmap.clear(coord_set[0], self.lmap)
                        else:
                            self.gui.vmap.drawSet(coord_set[0], coord_set[1])
                    self.gui.setStart(self.cfg["START"])
                    self.gui.setGoal(self.cfg["GOAL"])
                    self.fullsearchflag = True
                    self.coordsets = coord_sets
                    self.status_bar.set("Plotting path...", right_side=True)
                else:
                    # nextreturn just includes the next coordinate, no drawing data
                    next_step = next_return

                    # Paint path
                self.gui.vmap.drawSet(self.path, "blue")
                self.gui.vmap.drawPoint(next_step, "white")
                self.current = next_step
                self.path.add(next_step)

                if self.cfg.get("DEADLINE"):
                    self.status_bar.set(curr_step=next_step, cost=self.pathcost,
                                        no_steps=self.pathsteps, time_left=self.timeremaining)
                else:
                    self.status_bar.set(
                        curr_step=next_step, cost=self.pathcost, no_steps=self.pathsteps)

                time.sleep(self.cfg.get("SPEED"))  # delay, if any


    ################################################################################
    # MENU HANDLERS FOR THE GUI
    ################################################################################

    def loadMap(self, mapfile):
        """
        Menu handler: File - Open Map. Loads map based on openfiledialog in
        view. Creates new LogicalMap object and resets based on config

        :type mapfile: string
        """
        try:
            self.status_bar.set("Loading map...")
            self.lmap = LogicalMap(mapfile)

            # pass new LogicalMap references to Gui and MapCanvas (vmap)
            self.gui.setLmap(self.lmap)
            self.gui.vmap.drawMap(self.lmap)

        except:
            self.status_bar.set("Unable to load map: " + mapfile)

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
            self.status_bar.set(f"Start moved to {self.cfg['START']}")
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
            self.status_bar.set(f"Goal moved to {self.cfg['GOAL']}")

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

            self.status_bar.set(f"Initialised {agentfile}")
        except:
            self.status_bar.set(f"Unable to load {agentfile}")
            logging.error("Trace-back: \n {}".format(traceback.format_exc()))
            raise
        else:
            self.cfg["AGENT_FILE"] = agentfile


if __name__ == '__main__':
    logging.info(
        "To run the P4 Simulator, type 'python p4.py' at the command line and press <Enter>")
