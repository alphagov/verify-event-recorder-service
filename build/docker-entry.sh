#!/usr/bin/env bash
set -eu


service postgresql start
sudo -u postgres psql --command "alter user postgres with encrypted password 'secretPassword';"

curl -OL https://github.com/alphagov/verify-event-store-schema/archive/master.zip && unzip master.zip
tar -xzf verify-event-store-schema-master/flyway-commandline-5.0.7-linux-x64.tar.gz -C verify-event-store-schema-master

cd verify-event-store-schema-master

./flyway-5.0.7/flyway migrate \
    -locations=filesystem:../verify-event-store-schema-master/sql \
    -url=jdbc:postgresql://localhost:5432/postgres \
    -user=postgres -password=secretPassword

cd ..

echo "Running pip install..."
pip3 install -qr /usr/local/bin/requirements/dev.txt
echo "Pip install complete"
