#! /usr/bin/env bash

first="w\tb\tD\tmu\tTotalPrize\tPrizeInForest\tHiddenInForest\t"
first=$first"ProportionPrize\tAvgDegreePrize\tAvgDegreeHidden"

echo -e $first > $2

for d in $1/*/;
do
    ./forest_output_statistics.py $d >> $2
done

