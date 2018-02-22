#!/usr/bin/env bash

docker build -t event-recorder-image .
echo "Created container: $(docker create -t --name event-recorder-container event-recorder-image)"
echo "Started container: $(docker start event-recorder-container)"

docker cp . event-recorder-container:/event-recorder
docker exec -t --workdir /event-recorder event-recorder-container ./run-tests.sh

echo "Stopped container: $(docker stop event-recorder-container)"
echo "Removed container: $(docker rm event-recorder-container)"