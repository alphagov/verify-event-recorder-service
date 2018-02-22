#!/usr/bin/env bash

./start-docker.sh
docker exec -t --workdir /event-recorder event-recorder-container ./run-tests.sh
./kill-docker.sh
