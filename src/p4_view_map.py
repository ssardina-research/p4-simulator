# Copyright (C) 2014-17 Peta Masters and Sebastian Sardina
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

from tkinter import Canvas, PhotoImage, BOTH, NW, TclError

from p4_model import LogicalMap


class MapCanvas(Canvas):
    """
    Visual representation of map instantiated as a Tkinter.Canvas object.
    """

    def __init__(self, parent, top, lmap : LogicalMap):
        """Constructor. Initialises class attributes, calls drawMap. parent = mapcontainer
           created in Gui. Ref to Gui (top) supplied in case needed for future use."""
        Canvas.__init__(self, parent, width=512, height=512)
        # Bind drag and drop events to canvas and pack it in mapcontainer
        self.bind('<ButtonPress-1>', self.grab)
        self.bind('<ButtonRelease-1>', self.drop)
        self.bind('<B1-Motion>', self.drag)
        self.pack(side='left', fill=BOTH, expand=1)

        self.xpos = 0  # X coord of mouse grab event
        self.ypos = 0  # Y coord of mouse grab event
        self.scale = 1  # Current zoom level
        self.im = None  # Ref to original image, on which zoom is based
        self.original = None  # image id, as first added to canvas
        self.zoomed = None  # image id, as zoomed on canvas

        self.lmap = lmap
        self.drawMap(lmap)

    def grab(self, event):
        """Event handler. Displays fleur cursor and gets grab position"""
        self.ypos = event.y
        self.xpos = event.x
        self.config(cursor='fleur')

    def drop(self, event):
        """Event handler. Redisplays arrow cursor"""
        self.config(cursor='arrow')

    def drag(self, event):
        """Event handler. Scrolls canvas to new pos and updates old"""
        self.yview('scroll', self.ypos - event.y, 'units')
        self.xview('scroll', self.xpos - event.x, 'units')
        self.ypos = event.y
        self.xpos = event.x

    def reset(self):
        """Resets canvas to zoomlevel 1 and repositions top left"""
        self.xview_moveto(0)
        self.yview_moveto(0)
        self.zoomMap(1, 0, 0)

    def colorMap(self, char):
        """Effectively a switch statement to return color based on char"""
        return {
            '.': 'sienna',
            'G': 'sienna',
            'O': 'black',
            '@': 'black',
            'S': 'OliveDrab1',
            'T': 'green4',
            'W': 'SkyBlue3',
            'k': 'green3',
            'D': 'red'
        }[char]

    def drawMap(self, lmap : LogicalMap):
        """Creates new map image based on LogicalMap passed in lmap"""
        w = lmap.width
        h = lmap.height
        # set size of canvas and create bitmap of same size
        self.config(width=w, height=h, xscrollincrement=1, yscrollincrement=1)
        self.im = PhotoImage(width=w, height=h)
        # copy colors corresponding to lmap characters into bitmap and create on canvas
        for row in range(h):
            for col in range(w):
                if lmap.isKey((col, row)):
                    color = 'green3'
                elif lmap.isDoor((col, row)):
                    color = 'red'
                else:
                    color = self.colorMap(lmap.get_cell_type((col, row)))
                self.im.put(color, (col, row))
        self.original = self.create_image(0, 0, image=self.im, anchor=NW)

    def clear(self, points, lmap : LogicalMap):
        """Clears set of points by replacing each point with its original color,
           based on data in lmap"""
        for coord in points:
            if lmap.cellWithinBoundaries(coord):
                color = self.colorMap(lmap.get_cell_type(coord))
                self.im.put(color, coord)
        self.zoomMap(self.scale)

    def clearCross(self, coord, lmap : LogicalMap):
        """Clears cross at coord by replacing each point with its original color,
           based on data in lmap"""
        for n in range(-3, 3):
            color = self.colorMap(lmap.get_cell_type((coord[0] + n, coord[1] + n)))
            self._drawPoint(color, (coord[0] + n, coord[1] + n))
            color = self.colorMap(lmap.get_cell_type((coord[0] + n, coord[1] - n)))
            self._drawPoint(color, (coord[0] + n, coord[1] - n))
        self.zoomMap(self.scale)

    def drawCross(self, coord, color):
        """Draws cross at coord in nominiated color"""
        for n in range(-3, 3):
            self._drawPoint(color, (coord[0] + n, coord[1] + n))
            self._drawPoint(color, (coord[0] + n, coord[1] - n))
        self.zoomMap(self.scale)

    def drawSet(self, points, color):
        """Draws set of points in nominated color"""
        for coord in points:
            try:
                self.im.put(color, coord)
            except TclError:
                continue
        self.zoomMap(self.scale)

    def drawPoint(self, coord, color):
        """Draws individual point in nominated color"""
        try:
            self.im.put(color, coord)
            self.zoomMap(self.scale)
        except TclError:
            pass

    def _drawPoint(self, color, coord):
        """Internal. Draws individual point in nominated color without forcing displayed
        As elsewhere in view_map, assumes calling prog has checked for validity and forgives errors."""
        try:
            self.im.put(color, coord)
        except TclError:
            pass
            
    def zoomMap(self, scale, x=0, y=0):
        """Zooms map to scale. Also used to force changes to be displayed"""
        if self.zoomed:
            self.delete(self.zoomed)
        self.zoomed = self.im.zoom(scale, scale)
        zoomed_id = self.create_image(x, y, image=self.zoomed, anchor=NW)
        self.delete(self.original)
        self.scale = scale

    def getScale(self):
        """Getter. Returns scale.
        :rtype : float
        """
        return self.scale
