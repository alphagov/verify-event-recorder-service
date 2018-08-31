#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../"

TAG=event-recorder:package
NAME=event-recorder
docker build . -f package.Dockerfile -t $TAG
docker run --name $NAME $TAG
docker cp $(docker ps -a -q -f name="$NAME" | head -1):/package/verify-event-recorder-service.zip verify-event-recorder-service.zip
docker rm $NAME
