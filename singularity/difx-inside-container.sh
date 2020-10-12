#!/bin/bash

# this script runs inside of the Singularity container

DAY=$1
JOB=$2
INFIX="-0-b2_"

# set up environment
source /etc/bash.bashrc
# these are supposed to be set in /etc/bash.bashrc, why is it not working? XXX
source /usr/local/difx/bin/setup.bash
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/difx/lib
export PATH=$PATH:/usr/local/difx/bin

# get to the working directory
if [ "$PWD" != "$DAY" ]; then
  cd $DAY || exit 1
fi

if [ ! -e runmpifxcorr.DiFX-2.5.1 ]; then
    ln -s /usr/local/difx/bin/mpifxcorr runmpifxcorr.DiFX-2.5.1
fi

# difx exits if old output exists, so attempt to rename, adding our pid
if [ -d $DAY$INFIX$JOB.difx ]; then
    mv $DAY$INFIX$JOB.difx $DAY$INFIX$JOB.difx.$$
fi

# fix up the .machines and .threads files
../genmachines-onenode.py $DAY$INFIX$JOB

# we want to tell mpi to not attempt to pin any processes, because
# we use threads. This does the trick for OpenMPI:
export DIFX_MPIRUNOPTIONS="--oversubscribe"

startdifx -a $DAY$INFIX$JOB
