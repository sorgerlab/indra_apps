#! /usr/bin/env bash
# Perform a grid search, running the steiner tree algorithm for different
# parameter combinations in parallel. Requires GNU parallel to be installed


###############################################################################
# Config. Edit for your own uses
# Path to prize file

DIR=$(dirname "$0")
prize=$HOME/indra_apps/tubulin/work/EpoB1/EpoB_protein_prizes.tsv
# Path to interactome
edge=$HOME/indra_apps/tubulin/input/interactome.tsv
# Directory for output file. It will be created if it does not already exist
search=renewed_prize_search5
outpath=$HOME/indra_apps/tubulin/result/$search/output_w{1}_b{2}_D{3}_mu{4}
# Number of parallel jobs to perform
njobs=8

# Parameter lists for grid search
w="1"
b="10"
D="10"
mu="0.001"
###############################################################################

parallel --no-notice -j $njobs run_forest.sh -w {1} -b {2} -d {3} -u {4} \
	 $prize $edge $outpath ::: $w ::: $b ::: $D ::: $mu






		
