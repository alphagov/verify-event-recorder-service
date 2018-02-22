#!/usr/bin/env bash

docker build -t event-recorder-image .
docker create -t --name event-recorder-container event-recorder-image
docker start event-recorder-container

docker cp . event-recorder-container:/event-recorder
docker exec -t --workdir /event-recorder event-recorder-container ./run-tests.sh

docker stop event-recorder-container
docker rm event-recorder-container