#!/bin/bash
SLOTH_DIR=$1
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
SMARTPARKING_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

sudo apt-get install python python-pip python-qt4 -y
sudo pip2 install -U pip
sudo pip2 install importlib numpy Pillow
git clone https://github.com/cvhciKIT/sloth.git $SLOTH_DIR
cd $SLOTH_DIR
sudo python2.7 setup.py install
cp $SMARTPARKING_DIR/sloth/smartparking.py .
