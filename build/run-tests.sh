#!/usr/bin/env sh
set -e

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"

function stop_containers() {
  docker-compose down
}

trap stop_containers EXIT

if [[ -z "${VERIFY_EVENT_SYSTEM_DATABASE_SCRIPTS_LOCATION}" ]]; then
    export VERIFY_EVENT_SYSTEM_DATABASE_SCRIPTS_LOCATION=${SCRIPT_DIR}/../../verify-event-system-database-scripts
fi

echo Database Scripts are located at: ${VERIFY_EVENT_SYSTEM_DATABASE_SCRIPTS_LOCATION}

if [[ ! -d "${VERIFY_EVENT_SYSTEM_DATABASE_SCRIPTS_LOCATION}" ]]; then
    echo "Cloning database migration scripts repo..."
    pushd ${SCRIPT_DIR}/../..
    git clone git@github.com:alphagov/verify-event-system-database-scripts.git
    popd
fi

pushd ${SCRIPT_DIR}/.. > /dev/null
echo "Building test images..."
docker-compose build

echo "Starting up database..."
docker-compose up -d event-store

echo "Giving time for database to initialise..."
sleep 3

echo "Run database migrations..."
docker-compose run flyway migrate

echo "Run Tests..."
docker-compose run --rm tests
popd > /dev/null
