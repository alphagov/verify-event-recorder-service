#!/usr/bin/env bash

docker-compose build --no-cache
docker-compose run --rm tests
exit_code=$?
docker-compose down
exit $exit_code
