#! /usr/bin/env bash

repo_path=/home/albert/indra_apps/tubulin
first="w\tb\tD\tmu\tTotalPrize\tPrizeInForest\tHiddenInForest\t"
first=$first"ProportionPrize\tAvgDegreePrize\tAvgDegreeHidden"

echo -e $first > $2

for d in $1/*/;
do
    $(repo_path)/src/forest_output_statistics.py $d >> $2
done

