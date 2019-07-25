#!/usr/bin/env bash
set -e

function stop_containers() {
  docker-compose down
}

trap stop_containers EXIT

if [[ ! -d ../verify-event-system-database-scripts ]]; then
    echo "Cloning database migration scripts repo..."
    pushd ..
    git clone git@github.com:alphagov/verify-event-system-database-scripts.git
    popd
fi

echo "Building test imgages..."
docker-compose build

echo "Starting up database..."
docker-compose up -d event-store
docker-compose run flyway migrate

echo "Run Tests..."
docker-compose run --rm tests
