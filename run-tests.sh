#!/usr/bin/env bash
set -eu


echo "starting PostgreSQL"
service postgresql start
sudo -u postgres psql --command "alter user postgres with encrypted password 'secretPassword';"

echo "installing requirements"
pip3 install -r --user requirements.txt

echo "running tests"
python3 -m unittest discover test/ "*_test.py"