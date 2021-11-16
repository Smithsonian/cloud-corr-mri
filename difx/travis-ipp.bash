if [[ "$TRAVIS_IPP" == "TRUE" ]]; then
    sudo bash -c 'echo deb https://apt.repos.intel.com/ipp all main > /etc/apt/sources.list.d/intel-ipp.list'
    sudo wget https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
    sudo apt-key add GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
    sudo rm GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
    sudo apt-get update
    sudo apt-get install -y intel-ipp-2020.0-088
    IPPARG=""
else
    IPPARG="--noipp"
fi
