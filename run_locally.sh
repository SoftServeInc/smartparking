#!/bin/bash
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SMARTPARKING_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

cd $SMARTPARKING_DIR
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d video-server
sleep 60  # give some time to video server to initialize
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
