# ACG

[![Documentation Status](https://readthedocs.org/projects/acg/badge/?version=latest)](https://acg.readthedocs.io/en/latest/?badge=latest)

Arbitrary Cell Generator is a plugin to Berkeley Analog Generator 2.0 (BAG) which is described in detail in the following papers:
[BAG2: A Process-Portable Framework for Generator-Based AMS Circuit Design](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=8357061)
and [Closing the Analog Design Loop with Berkeley Analog Generator](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2019/EECS-2019-23.pdf).
Documentation for ACG can be found at <https://acg.readthedocs.io>. 
The main goal of ACG is to make it easy to create highly customized layout generators that may not be possible in BAG due to its
requirement to make layouts technology agnostic. In addition, we make it easy to combine legacy hand-drawn
layouts and IP together with new layout generators.

NOTE: ACG is currently in development, and is being slowly cleaned up for open-source consumption, use at your own risk!


## Unique Features
In short, BAG encourages a generator-based analog integrated circuit (IC) design methodology. 
This methodology enables the entire IC design procedure, from schematic design and simulation, to layout and optimization to be encapsulated in a set of Python scripts that are self-documenting, reproducible, reusable, and portable to different technologies and tapeouts.

ACG specifically aims to enhance the layout generation portion of the BAG flow.
Currently, BAG layout emphasizes the use of an abstraction layer called `AnalogBase`.
This class encapsulates the procedure of drawing transistor rows and metal routing in a way that is completely agnostic of the technology node you are using.
This makes porting design scripts from one technology to another extremely fast, but comes at the cost of losing some control over detailed layout optimizations.
In addition, incorporating `AnalogBase` cells together with hand-made cells and other external IP is not straightforward.

