#! /usr/bin/env bash


prize=../work/prize.txt
edge=../input/iref_mitab_miscore_2013_08_12_interactome.txt

parallel ./run_forest.sh -w {1} -b {2} -d {3} -u {4} $prize $edge \
	 ../work/grid_search/output_w{1}b{2}D{3}mu{4} ::: 5  ::: 1  ::: 5 1 \
	 ::: 0.001


		
