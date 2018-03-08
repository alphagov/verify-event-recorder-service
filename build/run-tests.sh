#!/usr/bin/env bash
set -eu

python3 -m unittest discover test/ "*_test.py"