#!/usr/bin/env bash

docker build -t event-emitter-image .
docker create -t --name event-emitter-container event-emitter-image
docker start event-emitter-container

docker cp . event-emitter-container:/event-emitter
docker exec -t --workdir /event-emitter event-emitter-container ./run-tests.sh

docker stop event-emitter-container
docker rm event-emitter-container