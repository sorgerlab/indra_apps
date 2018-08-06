#! /usr/bin/env bash
# Perform a grid search, running the steiner tree algorithm for different
# parameter combinations in parallel. C


###############################################################################
# Config. Edit for your own uses
# Path to prize file
prize=../input/bak_prizes.txt
# Path to interactome
edge=../input/iref_mitab_miscore_2013_08_12_interactome.txt
# Directory for output file. It will be created if it does not already exist
outpath=../result/bak_prize_search1/output_w{1}_b{2}_D{3}_mu{4}
# Number of parallel jobs to perform
njobs=8

# Parameter lists for grid search
w="1 5 10"
b="1 10 20"
D="5 10 15"
mu="0.0001 0.001 0.005"
###############################################################################

parallel --no-notice -j $njobs ./run_forest.sh -w {1} -b {2} -d {3} -u {4} \
	 $prize $edge $outpath ::: $w ::: $b ::: $D ::: $mu






		
