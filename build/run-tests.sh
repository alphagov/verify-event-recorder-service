#!/usr/bin/env bash
set -eu

service postgresql start
python3 -m unittest discover test/ "*_test.py"