# HIVE :honeybee:

**H**ighly  
**I**ntegrated  
**V**ehicle  
**E**cosystem  
  
HIVE is a mobility services research platform.  
  
## Setup

Setting up hive can be acomplished in a couple steps. First you need to 
make sure you have the right packages installed. An easy way to do this 
is to use conda which can be obtained here:

- https://www.anaconda.com/download/ (anaconda)
- https://conda.io/miniconda.html (miniconda)

To build the environment simply run:

    > conda env create -f environment.yml
    
Then, activate the environment with:

    > conda activate hive

That's it!

## Running a Scenario

Hive comes packaged with a demo scenario and some demo inputs. In order
to run our demo scenario we just need to navigate to the app/ sub directory
and run:

    > python run.py scenarios/denver_demo.yaml

This runs the demo scenario and writes outputs to `app/denver_demo_outputs`


