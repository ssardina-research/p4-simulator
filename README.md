# p4 - Python Path Planning Project


[p4 (aka the "Python Path Planning Project")](https://bitbucket.org/ssardina/soft-p4-sim-core) is a Python-based path planning framework and simulator, useful to prototype, evaluate, and benchmark path planning algoritms. The system began as a Python version of the Java-based [APPARATE path-planning simulator](https://bitbucket.org/ssardina-research/apparate-simulator) to be able to prototype algorithms in a "lighter" programming language. It started as part of Peta Master's 2013 programming course project and then extended to support her Honours thesis and doctorate program, under the supervision of A/Prof. Sebastian Sardina.

The p4 simulator relies on maps in the [Movingai](htpp://www.movingai.com) format. Run with GUI, to observe their operation, without GUI to obtain cost, steps and time-taken, or in auto mode to output `csv` files of accumulated results from map problems in `.scen` format (also from Movingai).

The p4 system has been used in the our [Goal Recognition in Path Planning AAMAS'17](https://dl.acm.org/citation.cfm?id=3091232) and the [Deception in Path Planning IJCAI'17](https://www.ijcai.org/proceedings/2017/610) papers. 
This [dedicated GR fork](https://bitbucket.org/ssardina-research/p4-simulator-gr) of this repo for the extensions to p4 related to those works; check the subfolders:

* For p4 in Goal Recognition in Path Planning see [here](https://bitbucket.org/ssardina-research/p4-simulator-gr/src/master/src/GR).
* For p4 in Deception in Path Planning see [here](https://bitbucket.org/ssardina-research/p4-simulator-gr/src/master/src/DPP).

Check some screenshots of p4: 
[screenshot 1](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot01.png) - 
[screenshot 2](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot02.png) - 
[screenshot 3](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot03.png) - 
[screenshot 4](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot04.png)


-----------------------
[TOC]

## Prerequisites

* Python 2.7
* python-tk - Tkinter - Writing Tk applications with Python
* Map in [Movingai](htpp://www.movingai.com) with extensions for cost modeling.

## Features

* Run from CLI (for benchmarking) or with GUI interface (for visualization and debugging).
* Compatible with [Movingai](htpp://www.movingai.com) map format with extensions for cost and dynamic changes (see below)
* Dynamic changes to map via map scripts (see below).
* Deadline specification (agent is terminated at deadline).
* Report of cost, steps, total and remaining time.
* Batch mode `-batch` for running group of scenarios (`.scen` format) and exporting stats to `csv` file.
* Different cost models: mixed, mixed-real, mixed-opt2.


## Director Structure

Supplied Files include:

* `docs/`: Documentation (not maintained beyond V2)
* `maps/`: Default map location
* `src/`: All source code for simulator
    * `src/argets/`:  Default agent location


## Usage

```
usage: p4.py [-h] [-m MAP_FILE] [-s START] [-g GOAL] [-a AGENT_FILE] [-nodiag]
             [-d DEADLINE] [-gui] [-e HEURISTIC] [-r SPEED] [-f FREE_TIME]
             [-c COST_MODEL] [-auto] [-version] [-dynamic] [-nonstrict] [-pre]
             [-batch [BATCH [BATCH ...]]]
             [CFG_FILE]
```

where:

* `CFG_FILE`: Configuration file with all settings as Python variables and includes information such as what map and search algorithm to use. See config.py for expected format.
If `config_file` or file path not supplied, looks for default `config.py`.
* `MAP_FILE` is a file in movingai format. if `MAP_FILE` is just a file name with no directory, it is assumed to be in `../maps/` sister folder.
* `START` is a tuple with start location in `(col,row)` format.
* `GOAL` is a tuple with goal location in `(col,row)` format.       
* `AGENT_FILE` is a file with prescribed API. If `AGENT_FILE` is just a file name with no directory, it is assumed to be in `./agents/` subfolder.
* `DEADLINE` is time limit in seconds, defaults to None.
* `HEURISTIC` may be euclid, manhattan or octile, defaults to euclid.
* `SPEED` is a time delay in seconds between moves, defaults to 0
* `FREE_TIME` steps returned within `FREE_TIME` (seconds) don't count towards total time.
* `COST_MODEL` is the cost model when using mixed-cost grids; it could be:
    * `mixed` (DEFAULT): one used in the contest using sqrt(2) for diagonals.
    * `straight`: moves are 1*cost of destination.
    * `diagonal`: moves are sqrt(2)*cost of destination.
    * `mixed-real`: full center-to-center cost between source and destination cell.
    * `mixed-opt1`: like mixed but optimized to 1.5.
    * `straight`: moves are 1*cost of destination.
    * `diagonal`: moves are 1.5*cost of destination.
    * `mixed-opt2`: like mixed but optimized to 1.5*2.  
    
    straight moves are 2 x cost of destination
    
    diagonal moves are 3*cost of destination

OPTIONS:

* `-h` - print help information
* `-nodiag` - disallows diagonal moves (default allows them)
* `-gui` - displays gui
* `-auto` - suppresses info messages and outputs result in csv format
* `-dynamic` - loads changes from script.py to occur during the search
* `-nonstrict` - permits traversal of impassable cells, albeit at infinite cost
* `-pre` - adds a call to agent.preprocess() before starting search
* `-realtime` - times every step (default times return of first step only)
* `-batch <SCEN_FILE> <OUT_FILE> [reps]` - reads problems from the `scen` file and outputs results to the `OUT_FILE` in csv format. Optionally takes integer `reps` for number of repetitions across which test times are to be averaged. 
    * The `<SCEN_FILE>` MUST be in Movingai scenario file format.  
    * The map to be used must be in the same directory as the `<SCEN_FILE>` and its name is the prefix up to `.map` included. For example, if the `<SCEN_FILE>`  is `../maps/bgmaps/AR0011SR.map.aopd.scen`, then the map to be used will be file `../maps/bgmaps/AR0011SR.map`. 
    * The map names inside the `.scen` file will be ignored. 


## Examples 

All run from folder `src/`:


- Run from customised config file and ASTAR in uniform cost with a deadline of 4 seconds:

        $ python p4.py altconfig.py
        Total Cost : 510.416305603 | Total Steps : 440 | Time Remaining : 19.519 | Total Time : 0.48086

        $ python p4.py -m ../maps/bloodvenomfalls.map -s 128,405 -g 403,93 -d 4 -a agent_astar
        Total Cost : 498.8320 | Total Steps : 421 | Time Remaining : inf | Total Time : 1.258769

    where:

    - _Total Cost_: total cost of the solution path; costs may be non-uniform and diagonal moves cost more than straight moves
    - _Total Steps_: number of steps that the path takes
    - _Time Remaining_: time left to deadline given
    - _Total Time_: time taken (Total Time + Time Remaining = Deadline)


- Run from default config file (`config.py`): `$ python p4.py`

- Run the GUI with a random agent:

    ```
    $ python p4.py -m AR0306SR.map  -s 218,110 -g 444,386 -a agent_random  -e euclid -d 20 -gui
    ```

- Run with mixed cost:

    ```
    $ python p4.py -m ../maps/bloodvenomfalls.map -c ../maps/mixedcost/G1-W5-S10.cost -s 128,405 -g 403,93 -a agent_astar
    ```

- Run a BATCH of scenarios described in AR0011SR.map.scen scenario file:
    * `astar_batch.csv` is where data will be written
    * 3 is the number of times the search is run on each problem instance (and then results averaged)
    * **Note:** if there's a difference between 'optimum' and astar 'actual', check SQRT2 definition in `p4_utils`.

    ```
    $ python p4.py -batch ../maps/bgmaps/AR0011SR.map.scen astar_batch.csv 3 -a agent_astar
    ```


- In `-auto` mode, output is in csv format: `cost;steps;time_taken;time_remaining`, e.g:
    
    `187.13708499;154;0.32759;19.672`


## Interrogate Model Outside Simulator

In the `src/` directory run the Python interpreter:

```
>>>import p4_model as m
>>>l = m.LogicalMap("../maps/mixedcost3.map")   #or other existing map
>>># now you can interrogate the model, e.g...
>>>l.getCost((0,0))                         #note double brackets
```


## Batch and Profiling (Unix only)


* Profile a run:
    * `-s time`: sorts by total time (without taking internal calls)
    * `-s comulative`: sorts by cummulative time (taking all internal calls into account)

    ```
    $ python -m cProfile p4.py -s time -m ../maps/AR0306SR.map  -s 218,110 -g 444,386 -a agent_astar -e euclid -d 20
    ```

* Run it 10 times and get the average time:

        $ run 10 /usr/bin/python  p4.py -m ../maps/AR0306SR.map  -s 218,110 -g 444,386 \
                -a agent_jps_inv -e euclid -d 20 | grep Cost | awk '{total += $19} END {print total/10}'

    Function `run()` should be defined (e.g., in `.bashrc`) as follows:
    
        \#function run
        run() {
            number=$1
            shift
            for i in `seq $number`; do
              bash $@
            done
        }


## Technical Information

* By default, algorithms are timed using `time.clock()`. Switch to `time.time()` by resetting the global variable in `p4_utils.py`. 
* `p4_utils` also controls colors used to display returned lists. 
* `p4_utils.py` provides settings and `p4_model.py` presents an interface you can interrogate when implementing your own `agents/` algorithms. 


## Contributors and Contact

* Peta Masters
* Sebastian Sardina

## License

This project is using the GPLv3 for open source licensing for information and the license visit GNU website (https://www.gnu.org/licenses/gpl-3.0.en.html).

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

----------------------------

## Screenshots

Blue agent navigating to destination:

![screenshot](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot01.png)

After arrival, area searched (closed list) is shown in yellow:


![screenshot](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot02.png)


A random agent:

![screenshot](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot03.png)


Use via terminal to do batch testing (many scenario problems in one map):

![screenshot](https://bitbucket.org/ssardina-research/p4-simulator/raw/master/docs/screenshots/screenshot03.png)

