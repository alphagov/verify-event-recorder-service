#!/usr/bin/env bash

echo "Stopped container: $(docker stop event-recorder-container)"
echo "Removed container: $(docker rm event-recorder-container)"