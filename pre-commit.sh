#!/usr/bin/env bash

pip3 install -r requirements.txt
python3  -m unittest discover test/ "*_test.py"
