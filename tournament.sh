#!/bin/sh

BOARDS=boards/tournament/*.txt

for board in $BOARDS
do
	echo -n "$board: "
	python chainshot.py -a3 -pq $board
done
