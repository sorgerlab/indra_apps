#! /usr/bin/env bash
# Perform a grid search, running the steiner tree algorithm for different
# parameter combinations in parallel. C


###############################################################################
# Config. Edit for your own uses
# Path to prize file

repo_path=/ext/indra_apps/tubulin
prize=$repo_path/work/EpoB_protein_prizes.tsv
# Path to interactome
edge=$repo_path/input/iref_mitab_miscore_2013_08_12_interactome.txt
# Directory for output file. It will be created if it does not already exist
outpath=$repo_path/result/tps_prize_search5/output_w{1}_b{2}_D{3}_mu{4}
# Number of parallel jobs to perform
njobs=16

# Parameter lists for grid search
w="5"
b="10"
D="5"
mu="0.01"
###############################################################################

parallel --no-notice -j $njobs ./run_forest.sh -w {1} -b {2} -d {3} -u {4} \
	 $prize $edge $outpath ::: $w ::: $b ::: $D ::: $mu






		
