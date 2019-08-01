#!/usr/bin/env bash

docker-compose build tests
docker-compose run --rm --no-deps --entrypoint "flake8 ." tests
exit_code=$?
docker-compose down
exit $exit_code
