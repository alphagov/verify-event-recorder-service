#!/usr/bin/env bash
set -eu

if [ -z "$(which python3)" ];
then
    echo -e "\033[31mError: Expected the alias 'python3' to exist\033[0m"
    echo -e "To install python3, run"
    echo -e "    brew install python3"
    exit 1
fi

pip3 install virtualenv
virtualenv --python=python3 event_recorder_virtualenv
pip3 install -r requirements.txt
