#!/bin/bash
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SMARTPARKING_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

sudo apt-get install python3 python3-pip libsm6 libxext6 libxrender-dev -y
sudo pip3 install -U pip
sudo pip3 install virtualenv
cd $SMARTPARKING_DIR
virtualenv venv --python=python3
source venv/bin/activate
pip3 install -r model/requirements.txt
