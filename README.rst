
===========
SameGame AI
===========

About
=====

This is a textual implementation of the game SameGame (also known as
Chainshot) with an AI based on best-first search. This project is for
a course in AI, which hopefully explains both its hackiness and its
oddities.

Usage
=====

You may execute the game by simply running::

    python chainshot.py

in the current directory. A collection of boards (namely those given
as examples in the project description) have been provided in text
files within the ``boards`` directory. When asked for the path to a
board, you may specify a relative path from the current directory.

Command-line interface
----------------------

There is also a command-line interface in order to ease both debugging
and comparsion runs. Use::

    python chainshot.py --help

in order to see a list of options.

Tournament
----------

To run the tournament gamut with the combined AI, execute::

    ./tournament.sh

