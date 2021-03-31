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

import signal

# https://docs.python.org/3/library/tk.html
# https://docs.python.org/3/library/tkinter.html
import tkinter
from tkinter.ttk import * # overwrites gui with smoother components where available
# from tkFileDialog import askopenfilename
from tkinter.filedialog import askopenfilename
# import tkinter.import tkMessageBox
import tkinter.messagebox
from p4_controller import SimController
from p4_model import LogicalMap

from p4_view_map import MapCanvas
import p4_utils as p4  # contains color constants


class Gui(tkinter.Tk):
    """
    Inherits from tkinter.Tk - i.e. this is top level window, with inherited
    methods used for buildGui().
    """

    def __init__(self, simref : SimController, lmap):
        """Calls buildGui and initialises variables."""
        tkinter.Tk.__init__(self, None)
        self.mode = tkinter.StringVar()  # auto updates statusbar L
        self.searchState = tkinter.StringVar()  # auto updates statusbar R
        self.simulator = simref  # ref to SimController
        self.lmap = lmap  # ref to LogicalMap
        self.toolmode = None
        self.keep = False
        self.show = False

        self._buildGui()

        self.savedstatus = ""  # to restore searchState after displaying cursor pos
        self.searchjob = None  # after id for step generator within searchStart()
        self.zoomjob = None  # after id for to delay zoombar operation
        self.searchtoggle = False  # True = searching, False = not searching

        # bring window to front
        self.attributes('-topmost', 1)
        #immediately cancel, so user can modify
        self.attributes('-topmost', 0)

    def _buildGui(self):
        """Internal. Called by constructor.
        Creates interface, inc menus, toolbar, mapholder, vmap, zoombar and statusbar
        """
        #window
        self.title('p4 Path Planning Simulator')
        w, h = self.winfo_screenwidth() - 250, self.winfo_screenheight() - 180

        # set size of window based on the map
        w, h = self.lmap.width + 50, self.lmap.height + 100
        self.geometry(f"{w}x{h}+0+0")

        #menu
        menubar = tkinter.Menu(self)

        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label='Open Map', command=self.openMap)
        filemenu.add_command(label='Reload Config File', command=self.reconfig)
        filemenu.add_separator()
        filemenu.add_command(label='Display Settings', command=self.settings)
        filemenu.add_separator()
        filemenu.add_command(label='Quit', command=self.quit)

        searchmenu = tkinter.Menu(menubar, tearoff=0)
        searchmenu.add_command(label='Load Agent', command=self.loadAgent)
        searchmenu.add_separator()
        searchmenu.add_command(label='Reset Start', command=self.resetStart)
        searchmenu.add_command(label='Reset Goal', command=self.resetGoal)

        helpmenu = tkinter.Menu(menubar, tearoff=0)
        helpmenu.add_command(label='About p4', command=self.about)
        helpmenu.add_command(label='Help', command=self.help)

        menubar.add_cascade(label='File', menu=filemenu)
        menubar.add_cascade(label='Search', menu=searchmenu)
        menubar.add_cascade(label='Help', menu=helpmenu)

        self.config(menu=menubar)  #show menu

        #toolbar
        toolbar = tkinter.Frame(self, borderwidth=1, relief='raised')
        self.btnSearch = tkinter.Button(toolbar, text="Play", relief='flat', command=self.hdl_play,
                                        state=tkinter.NORMAL)
        self.btnSearch.pack(side='left', padx=2, pady=2)
        self.btnPause = tkinter.Button(toolbar, text="Pause", relief='flat', command=self.searchPause,
                                       state=tkinter.DISABLED)
        self.btnPause.pack(side='left', padx=2, pady=2)
        self.btnStep = tkinter.Button(toolbar, text="Step", relief='flat', command=self.searchStep,
                                      state=tkinter.NORMAL)
        self.btnStep.pack(side='left', padx=2, pady=2)
        self.btnStop = tkinter.Button(toolbar, text="Stop", relief='flat', command=self.searchStop,
                                      state=tkinter.DISABLED)
        self.btnStop.pack(side='left', padx=2, pady=2)
        self.btnReset = tkinter.Button(toolbar, text="Reset", relief='flat', command=self.searchReset,
                                       state=tkinter.DISABLED)
        self.btnReset.pack(side='left', padx=2, pady=2)
        toolbar.pack(side='top', fill='x')

        #modebar
        modebar = tkinter.Frame(self, borderwidth=1, relief='raised')
        self.btnS = tkinter.Button(toolbar, text="X", relief='flat', command=self.startMode, state=tkinter.NORMAL, \
                                   background="gray", foreground="green")
        self.btnS.pack(side='left', padx=2, pady=2)
        self.btnG = tkinter.Button(toolbar, text="X", relief='flat', command=self.goalMode, state=tkinter.NORMAL, \
                                   background="gray", foreground="tomato")
        self.btnG.pack(side='left', padx=2, pady=2)

        self.btnKeep = tkinter.Button(toolbar, text="Keep", relief='flat', command=self.keepPath, state=tkinter.NORMAL)
        self.pin = tkinter.PhotoImage(file="graphics/pin1.gif")
        self.btnKeep.config(image = self.pin)
        self.btnKeep.pack(side='left', padx=2, pady=2)

        self.btnShow = tkinter.Button(toolbar, text="Show", relief='flat', command=self.showWorkings, state=tkinter.NORMAL)
        self.btnShow.pack(side='left', padx=2, pady=2)

        modebar.pack(side="left")

        #maparea
        self.mapholder = tkinter.Frame(self)
        self.mapholder.pack(fill=tkinter.BOTH, expand=1)

        self.vmap = MapCanvas(self.mapholder, self, self.lmap)
        self.vmap.bind_all('<Key>', self.key)  #bind events to canvas
        self.vmap.bind('<Motion>', self.motion)
        self.vmap.bind('<Button-1>', self.click)

        #statusbar
        statusbar = tkinter.Frame(self, borderwidth=1, relief='sunken')

        #child zoombar
        self.zoombar = tkinter.Scale(statusbar, command=self.slider, orient='horizontal', from_=0, to=4, length=120, \
                                     showvalue=0)
        self.zoombar.pack(side='right')

        #child label
        #set message to change when self.mode variable changes
        statusmessage = tkinter.Label(statusbar, textvariable=self.mode, anchor=tkinter.W, justify=tkinter.LEFT)
        statusmessage.pack(side='left')

        #set message to change when self.searchState variable changes
        statusstate = tkinter.Label(statusbar, textvariable=self.searchState, anchor=tkinter.E, justify=tkinter.RIGHT)
        statusstate.pack(side='right')

        statusbar.pack(side='bottom', fill='x')

    ####################################################################################
    # GETTERS & SETTERS
    ####################################################################################
    def setLmap(self, lmap):
        """sets lmap attribute in case of reset"""
        self.lmap = lmap

    def resetZoom(self):
        """sets zoom slider to zero"""
        self.zoombar.set(0)

    def resetPos(self):
        """calls reset on MapCanvas object - which repositions map and resets zoom to 1"""
        self.vmap.reset()

    def setStart(self, start):
        """draws cross at start position"""
        self.vmap.drawCross(start, p4.COLOR_START)
        self.start = start  #position is saved, so it can be cleared

    def setGoal(self, goal):
        """draws cross at goal position"""
        self.vmap.drawCross(goal, p4.COLOR_GOAL)
        self.goal = goal  #position is saved, so it can be cleared

    def clearPoints(self, pointlist):
        """sends list of points to vmap to be redrawn/cleared 
        based on current lmap"""
        self.vmap.clear(pointlist, self.lmap)

    ####################################################################################
    # EVENT HANDLERS
    ####################################################################################
    def key(self, event):
        """Event handler. Listens for S or s and calls SimController to toggle pause/play"""
        if event.char == "s" or event.char == "S":
            self.searchtoggle = not self.searchtoggle
            if self.searchtoggle:
                self.hdl_play()
            else:
                self.searchPause()

    def motion(self, event):
        """Event handler. Listens for mouse on canvas and displays coord at status right."""
        scale = self.vmap.getScale()
        x = self.vmap.canvasx(event.x) / scale
        y = self.vmap.canvasy(event.y) / scale
        if x >= 0 and y >= 0 and x <= self.lmap.width - 1 and y <= self.lmap.height - 1:
            self.setStatusR(f"({int(x)}, {int(y)})", keep=False)
        else:
            #restore saved status when mouse moves off canvas
            self.setStatusR(self.savedstatus)

    def click(self, event):
        """Event handler. If toolmode is set, clicking the map resets the goal
           or start position. Else, click passes event to MapCanvas.grab to
           process the map drag and drop."""
        scale = self.vmap.getScale()
        x = int(self.vmap.canvasx(event.x) / scale)
        y = int(self.vmap.canvasy(event.y) / scale)
        if x >= 0 and y >= 0 and x <= self.lmap.width - 1 and y <= self.lmap.height - 1:
            pos = self.lmap.nearestPassable((x, y))
            if self.toolmode == "G":
                self.vmap.clearCross(self.goal, self.lmap)
                self.simulator.setGoal(pos)
                self.toolmode = None
                self.btnG.config(background="gray", relief="flat")
            elif self.toolmode == "S":
                self.vmap.clearCross(self.start, self.lmap)
                self.simulator.setStart(pos)
                self.toolmode = None
                self.btnS.config(background="gray", relief="flat")
            else:
                self.btnReset.config(state=tkinter.NORMAL)  #if map is moved, allow it to be reset
                self.vmap.grab(event)


    def slider(self, event):
        """Event handler. Calls nested actionZoom function on delay to perform zoom on map.
           (Without embedded delay, zoom keeps trying to reset and becomes unusable)"""

        def actionZoom():
            #nested method does the actual zooming
            value = 2 ** self.zoombar.get()
            self.vmap.zoomMap(value, 0, 0)

        if self.zoomjob:
            self.after_cancel(self.zoomjob)
        self.zoomjob = self.after(100, actionZoom)

    ####################################################################################
    # MENU LISTENERS
    ####################################################################################
    def openMap(self):
        """Menu listener. Displays openfile dlg then hands off to SimController"""
        mapfile = askopenfilename(filetypes=[("Map files", "*.map")], initialdir=["../maps"])
        if mapfile:
            self.simulator.loadMap(mapfile)

    def reconfig(self):
        """Menu listener. Clears crosses from map, then SimController reloads config file"""
        self.vmap.clearCross(self.start, self.lmap)
        self.vmap.clearCross(self.goal, self.lmap)
        self.simulator.read_config()

    def settings(self):
        """Menu listener. Displays current config settings"""
        stgs = self.simulator.getSettings()
        msg = ""
        for k, v in sorted(stgs.iteritems()):
            if not k == "__builtins__" and not k == "MAPREF":  #disregard junk/undisplayable
                msg = msg + k + " : " + str(v) + "\n"
        self.mBox(msg)

    def about(self):
        """Menu listener. Displays Help-About dialog"""
        aboutmsg = "p4 is a Python Path Planning Simulator " + \
                   "\nbased on the Java application Apparate." + \
                   "\n\nFirst implemented by Peta Masters for her " + \
                   "\nProgramming Project S2, 2013." + \
                   "\n\nVersion 3.0, 2017"
        self.mBox(aboutmsg)

    def help(self):
        """Menu listener. Displays Help-Help dialog"""
        helpmsg = "Use the buttons to control the search or hit\n" \
                  + "'S' to toggle search between play and pause.\n" \
                  + "Drag the slider to zoom the map.\n" \
                  + "Click and drag the map to move it around.\n" \
                  + "Click a cross then the map to reposition a \n" \
                  + " start or goal marker.\n" \
                  + "Click pin to keep current path during 2nd search.\n" \
                  + "Click Show to display open and closed lists \n" \
                  + "(if supported by current agent).\n\n" \
                  + "If you open a new map (File Menu), new start \n" \
                  + " and goal positions will be randomly selected.\n" \
                  + "For more extensive changes, modify the config file\n" \
                  + " and reload it (File Menu).\n\n" \
                  + "To vary the search, try a different agent \n" \
                  + " (Search Menu) - or write your own!"
        self.mBox(helpmsg)

    def loadAgent(self):
        """Menu listener. Displays openfile dlg then hands off to SimController"""
        agentfile = askopenfilename(filetypes=[("Agent Files", "*.py")], initialdir=["./agents"])
        if agentfile:
            self.simulator.loadAgent(agentfile)

    def resetStart(self):
        """Menu listener. Clears cross from old pos and calls SimController to reset """
        self.vmap.clearCross(self.start, self.lmap)
        self.simulator.setStart()

    def clearGoal(self):
        self.vmap.clearCross(self.goal, self.lmap)

    def clearStart(self):
        self.vmap.clearCross(self.start, self.lmap)

    def resetGoal(self):
        """Menu listener. Clears cross from old pos and calls SimController to reset """
        self.clearGoal()
        self.simulator.setGoal()

    def mBox(self, msg):
        """Displays message in dialog box. Returns True when user clicks OK"""
        x = tkinter.messagebox.showinfo(message=msg)
        return x == 'ok'

    ####################################################################################
    # BUTTON LISTENERS
    ####################################################################################
    def hdl_play(self):
        """
        Button listener.  This is used only on GUI mode.

        Calls nested generator (step) using after function.
        Step hands off to SimController.hdlStep(), testing against arrived and outOfTime.
        If either is True, calls terminateSearch()

        Any event handler has to return quickly for the GUI to be responsive.
        We can do this by using .after repetitively and yielding to GUI (here) or via threading:

        https://www.reddit.com/r/Python/comments/7rp4xj/threading_a_tkinter_gui_is_hell_my_least_favorite/
        """
        def step():
            if self.simulator.out_of_time():
                self.terminateSearch("Timeout!")
            elif self.simulator.arrived():
                self.terminateSearch("Arrived!")
            else:
                try:
                    self.make_one_step()
                except p4.BadAgentException:
                    self.terminateSearch("Unable to process next step!")
                else:
                    # schedule next step; do not use step()! - covert speed in sec to msec
                    self.searchjob = self.after(max(1, int(float(self.simulator.cfg.get("SPEED"))*1000)), step)    

        # def step():
        #     if self.simulator.out_of_time():
        #         self.terminateSearch("Timeout!")
        #     elif self.simulator.arrived():
        #         self.terminateSearch("Arrived!")
        #     else:
        #         try:
        #             self.simulator.hdl_step()
        #         except p4.BadAgentException:
        #             self.terminateSearch("Unable to process next step!")
        #         else:
        #             # schedule next step; do not use step()! - covert speed in sec to msec
        #             self.searchjob = self.after(max(1, int(float(self.simulator.cfg.get("SPEED"))*1000)), step)    


        self._setButtonStates(0, 1, 0, 1, 0)
        self.setStatusR("Stepping...")
        self.searchToggle = True
        self.searchjob = self.after(1, step())

    def make_one_step(self):
        """Button handler. Only used for in GUI mode.
            Performs one step for GUI.

           Checks for goal, calls gen to get next step from agent, displays step on map,
           and updates status bar. If "SPEED" set, inserts delay.

           Note: delay occurs whether called as single step or within
           continuous search; with step, the delay is unnoticeable because of the time
           taken to click the button again."""
        if not self.simulator.current == self.simulator.cfg["GOAL"] and self.simulator.time_remaining:
            try:
                with p4.Timeout(self.simulator.time_remaining):  # call under SIGNAL
                    # get the next step from the agent; either:
                    #  (x, y): next step from the agent
                    #  ((x,y), ((list1, col1),...,(listn, coln))): next coord + working lists with colors to drw
                    next_step = next(self.simulator.gen)
            except p4.Timeout.Timeout:
                self.simulator.time_remaining = -1.0
                self.show_status("Time Out!", right_side=True)
            except StopIteration:   # no next step provided!
                self.simulator.path_steps = -1
                self.simulator.path_time = float('inf')
                self.terminateSearch("No plan found!")
            except Exception as e:
                self.show_status(f"Agent returned exception on new step: {e}", right_side=False)
                raise e
            else:  # try/except/else...
                # does nextreturn include a list of coordinates to draw?
                next_coord = self.simulator.get_coordinate(next_step)
                coord_sets = self.simulator.get_drawing_lists(next_step)
                if coord_sets:
                    for coord_set in coord_sets:
                        if coord_set[1] == 'reset':
                            self.vmap.clear(coord_set[0], self.simulator.lmap)
                        else:
                            self.vmap.drawSet(coord_set[0], coord_set[1])
                    self.setStart(self.cfg["START"])
                    self.setGoal(self.cfg["GOAL"])
                    self.simulator.fullsearchflag = True
                    self.simulator.coord_sets = coord_sets
                    self.show_status("Plotting path...", right_side=True)

                # Paint path
                self.vmap.drawSet(self.simulator.path, "blue")
                self.vmap.drawPoint(next_coord, "white")
                self.simulator.current = next_coord
                self.simulator.path.add(next_coord)

                self.simulator.show_status(curr_step=next_coord)

    def hdl_reset(self, msg="OK"):
        """Button handler. Clears map, resets GUI and calls setVars"""
        if self.simulator.have_script:
            self.simulator.lmap = LogicalMap(
                os.path.join("../maps/", self.simulator.cfg["MAP_FILE"]))
            self.setLmap(self.simulator.lmap)
            self.vmap.drawMap(self.simulator.lmap)
            self.simulator.cfg["GOAL"] = self.simulator.goal_changes["ORIGIN"]

        else:
            # clear map
            self.vmap.clear(self.simulator.path, self.simulator.lmap)
            if self.simulator.fullsearchflag:
                self.show_status("Redrawing map")
                self.show_status("Please wait...", right_side=False)
                for (a, b) in self.simulator.coord_sets:
                    self.vmap.clear(a, self.simulator.lmap)
                self.simulator.fullsearchflag = False
                self.show_status("", right_side=False)
            # resize and reposition
            self.resetPos()
            self.resetZoom()
        # reset vars
        self.simulator.reset_vars()
        self.simulator.agent.reset()

        self.simulator.setStart(self.simulator.cfg["START"])
        self.simulator.setGoal(self.simulator.cfg["GOAL"])
        if self.simulator.keptpath:
            self.vmap.drawSet(self.simulator.keptpath, "orange")
        self.cancelWorkings()
        self.show_status(msg)
        self.show_status("", right_side=True)  # clears RIGHT statusbar



    def searchPause(self):
        """Button listener. Cancels after call to search generator, sets searchToggle"""
        self.after_cancel(self.searchjob)
        self._setButtonStates(1, 0, 1, 1, 0)
        self.setStatusR("Paused...")
        self.searchToggle = False

    def searchStep(self):
        """Button listener. Makes single call to SimController's hdlStep function"""
        self._setButtonStates(1, 0, 1, 1, 0)
        self.setStatusR("Paused...")
        self.searchToggle = False
        self.make_one_step()

    def searchStop(self):
        """Button listener. Cancels 'after' call to search generator, calls SimController's
           hdlStop function"""
        try:
            self.after_cancel(self.searchjob)
        except ValueError:
            pass # the job has been completed anyways
        self._setButtonStates(0, 0, 0, 0, 1)
        self.setStatusR("Stopped.")
        self.searchToggle = False

    def searchReset(self):
        """Button listener. Resets buttons and calls simulator's hdlReset function."""
        self._setButtonStates(1, 0, 1, 0, 0)
        self.setStatusR("")
        self.searchToggle = False
        self.hdl_reset()

    def terminateSearch(self, msg):
        """
        Cancels after call to search generator, resets button states, displays msg,
           cancels signal - in case of timeout - and calls SimController's hdlStop
        """
        # I removed this March 28, 2021, not sure why it is needed... :-)
        if self.searchjob: 
            self.after_cancel(self.searchjob)
        self._setButtonStates(0, 0, 0, 0, 1)
        self.setStatusR(msg)
        self.searchToggle = False
        try:
            signal.alarm(0)  # cancel signal
        except AttributeError:
            pass

    def _setButtonStates(self, sea=0, pau=0, ste=0, sto=0, res=0):
        """Internal. Lets button listeners enable/disable button states as required"""
        buttonstate = {0: tkinter.DISABLED,
                       1: tkinter.NORMAL}
        self.btnSearch.config(state=buttonstate[sea])
        self.btnPause.config(state=buttonstate[pau])
        self.btnStep.config(state=buttonstate[ste])
        self.btnStop.config(state=buttonstate[sto])
        self.btnReset.config(state=buttonstate[res])


    ####################################################################################
    # HANDLE STATUSBAR UPDATES
    ####################################################################################
    def show_status(self, msg, right_side=False, keep=True):
        """
        By default, show msg on left panel
        """
        if right_side:
            self.setStatusR(msg, keep)
        else:
            self.setStatusL(msg, keep)

    def setStatusR(self, value, keep=True):
        """Writes to status bar - R"""
        if keep:
            self.savedstatus = value
        self.searchState.set(value)
        self.update_idletasks() # force immediate update

    def setStatusL(self, value, keep=True):
        """Writes to status bar - L"""
        self.mode.set(value)
        self.update_idletasks() # force immediate update

    ####################################################################################
    # OTHER WIDGET HANDLERS
    ####################################################################################
    def goalMode(self):
        """handle red cross toggle"""
        if self.toolmode == "G":
            self.toolmode = None
            self.btnG.config(relief="flat")

        else:
            self.toolmode = "G"
            self.btnG.config(relief="ridge")
            self.btnS.config(relief="flat")

    def startMode(self):
        """handle green cross toggle"""
        if self.toolmode == "S":
            self.toolmode = None
            self.btnG.config(relief="flat")
        else:
            self.toolmode = "S"
            self.btnS.config(relief="ridge")
            self.btnG.config(relief="flat")

    def keepPath(self):
        """keep currently displayed path"""
        if self.keep == True:
            self.keep = False
            self.btnKeep.config(relief="flat")
            self.simulator.losePath()
        else:
            self.keep = True
            self.btnKeep.config(relief="ridge")
            self.simulator.keepPath()

    def cancelWorkings(self):
        self.show = False
        self.btnShow.config(relief="flat")

    def showWorkings(self):
        """user wants to see closed/open lists"""
        if self.show == True:
            self.show = False
            self.btnShow.config(relief="flat")
            self.simulator.hideWorkings()
        else:
            self.show = True
            self.btnShow.config(relief="ridge")
            self.simulator.showWorkings()

