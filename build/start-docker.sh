#!/usr/bin/env bash

docker build -t event-recorder-image .
echo "Created container: $(docker create -t -p 5432:5432 --name event-recorder-container event-recorder-image)"
echo "Started container: $(docker start event-recorder-container)"

docker cp . event-recorder-container:/event-recorder