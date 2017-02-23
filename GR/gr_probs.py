"""
GR problem generator inputs scen filename + optionally number of problems, 
number of extra goals, buffer required between start/goals, output filename.
If no output filename, outputs to src directory, 
to scen name with extra ".GR" extension.
File trims unneeded data and adds extra goal coords.
scenfile name must be map name + .scen (even if .scen file contains a different
map name) and map must be in same directory as .scen file

Sample CLI:
python gr_probs.py ..\maps\dpp\AR0316SR.map.scen 5 4 30 ..\maps\baldurs\testout.gr
"""

import argparse, os, csv, sys
from random import randint
from random import random
from p4_model import LogicalMap

#Create parser
parser = argparse.ArgumentParser(description="GR problem generator")
parser.add_argument('infile', type = file)
parser.add_argument('numprobs', nargs='?', type=int, default = 15)
parser.add_argument('maxgoals', nargs='?', type=int, default = 5)
parser.add_argument('buffer', nargs='?', type = int, default = 30)
parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'))
try:
    args = parser.parse_args()
except IOError, e:
    print str(e)
    sys.exit(1)

if not args.outfile:
    temp = args.infile.name + ".GR"
    args.outfile = open(temp, 'wb')

# write headers
csvout = csv.writer(args.outfile, delimiter=',')
headerlist = ['map', 'optcost', '#goals', 'start_x', 'start_y', 'goal0_x', 'goal0_y']
for i in range(args.maxgoals):
    headerlist.append('goal' + str(i) + '_x')
    headerlist.append('goal' + str(i) + '_y')
csvout.writerow(headerlist)   

# read scenfile into problems list
problems = [line.strip().split() for line in args.infile if len(line) > 20]
args.infile.close()

totalprobs = float(len(problems))

someprobs = [prob for prob in problems if random() <= args.numprobs/totalprobs]

print len(someprobs)
#get mapname from scen name
mapname = args.infile.name[:-5]
pathname, map = os.path.split(mapname)
#create model
model = LogicalMap(mapname)
#for each problem
for problem in someprobs:
    #read problem from .scen
    _, _, _, _, scol, srow, gcol, grow, optcost = problem
    if float(optcost) < args.buffer:
        continue
    numgoals = randint(2, args.maxgoals)
    #build writelist for new problem
    writelist = [map, optcost, numgoals, scol, srow, gcol, grow]
    #generate extra goals
    for i in range(numgoals):
        goal = model.generateCoord()
        writelist.extend([goal[0],goal[1]])
    csvout.writerow(writelist)
    
    #if that's the required number of problems, quit       
    args.numprobs = args.numprobs - 1
    if not args.numprobs:
        break
args.outfile.close()       
