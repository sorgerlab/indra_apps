#! /usr/bin/env bash

#########################################################
#Wrapper around the forest.py script in Omics Integrator
# Automates generation of temporary config files 
#Albert Steppi 7.27.2018
#########################################################

# Change to the path to your own forest.py script
forestpath=/home/ubuntu/albert/OmicsIntegrator-0.3.1/scripts/forest.py
msgpath=/home/ubuntu/albert/bin/msgsteiner

# Default parameters
w=5 # controls the number of trees in output
d=10 # maximum depth from the dummy node
b=2 # controls the number of terminal nodes included
u=0 # penalize hubs with high degree

# parse flagged arguments
while getopts 'w:d:b:u:' option
do
    case "$option" in 
	w) w="$OPTARG";;
	d) d="$OPTARG";;
	b) b="$OPTARG";;
	u) u="$OPTARG";;
    esac
done

# positional arguments
prize=${@:$OPTIND:1}
edge=${@:$OPTIND+1:1}
outpath=${@:$OPTIND+2:1}

# if the specified output directory does not exist, create it
mkdir -p $outpath

# Create a temporary folder for storing forest's config file
conf=$(mktemp -d "$TMPDIR/$(basename $0).XXXXXXXXXXXXX")
cat <<EOF>> $conf/forest_cfg
w = $w
D = $d
b = $b
mu = $u
EOF

python $forestpath --msgpath=$msgpath --prize=$prize --edge=$edge --outpath=$outpath --conf=$conf/forest_cfg

# Add the generated conf file to the output folder so we can recover
# the parameters later
cp -r $conf/forest_cfg $outpath

# cleanup temporary files on exit
trap "{ rm -rf $conf; }" EXIT
