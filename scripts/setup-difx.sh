# needs to be run with .

echo 'you should have already run ". greg.sh"'

pushd ~/github/difx-try4-with-ipp 
DIFXROOT_OVERRIDE=$PWD . setup.bash
source $DIFXROOT/bin/hops.bash
popd

echo "difx and hops should be initialized"
