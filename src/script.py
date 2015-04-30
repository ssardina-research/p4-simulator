# Copyright (C) 2015 Peta Masters and Sebastian Sardina
"""if script.py exists in the src directory it will be loaded and actioned.
GOAL_CHANGE, AGENT_CHANGE and TERRAIN_CHANGE must exist as dictionary variables
but they can be empty. e.g. 
GOAL_CHANGE = {}
AGENT_CHANGE = {}
TERRAIN_CHANGE = {}
"""

#Move goal to a new coordinate
#format: 
#step: (col, row)
GOAL_CHANGE = {
    30: (255,101),
    60: (282,407),
}

#Move agent relative to current position
#format: 
#step: (relative col, relative row)
AGENT_CHANGE = {
    #40: (-5, 0),
    #70: (2, 3),
}
    
#Modify underlying map - add terrain type from top left to bottom right
#format: 
#step: (terrain, (col, row), (col, row))
TERRAIN_CHANGE = {
    10: ('T', (100,100), (110,110)),
    50: ('@', (126,142), (144, 150)),
}

