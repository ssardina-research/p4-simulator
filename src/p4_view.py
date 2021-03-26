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

import tkinter
from tkinter.ttk import * # overwrites gui with smoother components where available
# from tkFileDialog import askopenfilename
from tkinter.filedialog import askopenfilename
# import tkinter.import tkMessageBox
import tkinter.messagebox

from p4_view_map import MapCanvas
import p4_utils as p4  # contains color constants


class Gui(tkinter.Tk):
    """
    Inherits from tkinter.Tk - i.e. this is top level window, with inherited
    methods used for buildGui().
    """

    def __init__(self, simref, lmap):
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

    # GETTERS & SETTERS
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
        self.vmap.drawCross(start, p4.COL_START)
        self.start = start  #position is saved, so it can be cleared

    def setGoal(self, goal):
        """draws cross at goal position"""
        self.vmap.drawCross(goal, p4.COL_GOAL)
        self.goal = goal  #position is saved, so it can be cleared
        
    def clearPoints(self, pointlist):
        """sends list of points to vmap to be redrawn/cleared 
        based on current lmap"""
        self.vmap.clear(pointlist, self.lmap)

    #EVENT HANDLERS
    def key(self, event):
        """Event handler. Listens for S or s and calls SimController to toggle pause/play"""
        if event.char == "s" or event.char == "S":
            self.searchtoggle = not self.searchtoggle
            if self.searchtoggle:
                self.searchStart()
            else:
                self.searchPause()

    def motion(self, event):
        """Event handler. Listens for mouse on canvas and displays coord at status right."""
        scale = self.vmap.getScale()
        x = self.vmap.canvasx(event.x) / scale
        y = self.vmap.canvasy(event.y) / scale
        if x >= 0 and y >= 0 and x <= self.lmap.width - 1 and y <= self.lmap.height - 1:
            self.setStatusR("(" + str(int(x)) + "," + str(int(y)) + ")", False)
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

    #MENU LISTENERS
    def openMap(self):
        """Menu listener. Displays openfile dlg then hands off to SimController"""
        mapfile = askopenfilename(filetypes=[("Map files", "*.map")], initialdir=["../maps"])
        if mapfile:
            self.simulator.loadMap(mapfile)

    def reconfig(self):
        """Menu listener. Clears crosses from map, then SimController reloads config file"""
        self.vmap.clearCross(self.start, self.lmap)
        self.vmap.clearCross(self.goal, self.lmap)
        self.simulator.readConfig()

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
        x = tkMessageBox.showinfo(message=msg)
        return x == 'ok'

    # BUTTON LISTENERS
    def searchStart(self):
        """Button listener. Calls nested generator (step) using after function. Step
           hands off to SimController.hdlStep(), testing against areWeTereYet and outOfTime.
           If either is True, calls terminateSearch()"""
        self._setButtonStates(0, 1, 0, 1, 0)

        self.setStatusR("Searching...")
        self.searchToggle = True

        # Nested generator returns control to GUI between steps
        def step():
            while True:
                try:
                    self.simulator.hdlStep()
                except p4.BadAgentException:
                    self.terminateSearch("Unable to process next step!")
                else:
                    if not self.simulator.areWeThereYet() and not self.simulator.outOfTime():
                        self.searchjob = self.after(1, next(step()))
                    elif self.simulator.outOfTime():
                        self.terminateSearch("Timeout!")
                    else:
                        self.terminateSearch("Arrived!")
                finally:
                    yield
        
        if self.simulator.areWeThereYet():
            self.terminateSearch("Arrived!")
        else:
            self.searchjob = self.after(1, next(step()))
        

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
        self.simulator.hdlStep()

    def searchStop(self):
        """Button listener. Cancels 'after' call to search generator, calls SimController's
           hdlStop function"""
        self.after_cancel(self.searchjob)
        self._setButtonStates(0, 0, 0, 0, 1)
        self.setStatusR("Stopped.")
        self.searchToggle = False
        self.simulator.hdlStop()

    def searchReset(self):
        """Button listener. Resets buttons and calls simulator's hdlReset function."""
        self._setButtonStates(1, 0, 1, 0, 0)
        self.setStatusR("")
        self.searchToggle = False
        self.simulator.hdlReset()

    def terminateSearch(self, msg):
        """Cancels after call to search generator, resets button states, displays msg,
           cancels signal - in case of timeout - and calls SimController's hdlStop"""
        self.after_cancel(self.searchjob)
        self._setButtonStates(0, 0, 0, 0, 1)
        self.setStatusR(msg)
        self.searchToggle = False
        try:
            signal.alarm(0)  # cancel signal
        except AttributeError:
            pass
        self.simulator.hdlStop()

    def _setButtonStates(self, sea=0, pau=0, ste=0, sto=0, res=0):
        """Internal. Lets button listeners enable/disable button states as required"""
        buttonstate = {0: tkinter.DISABLED,
                       1: tkinter.NORMAL}
        self.btnSearch.config(state=buttonstate[sea])
        self.btnPause.config(state=buttonstate[pau])
        self.btnStep.config(state=buttonstate[ste])
        self.btnStop.config(state=buttonstate[sto])
        self.btnReset.config(state=buttonstate[res])

    #HANDLE STATUSBAR UPDATES
    def setStatusR(self, value, keep=True):
        """Writes to status bar - R"""
        if keep:
            self.savedstatus = value
        self.searchState.set(value)
        #force immediate update
        self.update_idletasks()

    def setStatusL(self, value):
        """Writes to status bar - L"""
        self.mode.set(value)
        #force immediate update
        self.update_idletasks()

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
            
    #Initialise GUI
    def _buildGui(self):
        """Internal. Called by constructor. Creates interface, inc menus, toolbar,
           mapholder, vmap, zoombar and statusbar"""
        #window
        self.title('p4 Path Planning Simulator')
        w, h = self.winfo_screenwidth() - 50, self.winfo_screenheight() - 100
        self.geometry("%dx%d+0+0" % (w, h))

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
        self.btnSearch = tkinter.Button(toolbar, text="Play", relief='flat', command=self.searchStart,
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
