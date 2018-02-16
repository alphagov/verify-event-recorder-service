#!/usr/bin/env bash


if [ -z "$(which python3)" ];
then
    echo "install"
    brew install python3
else
    echo "update"
    brew upgrade python3
fi

pip3 install virtualenv
virtualenv --python=python3 event_recorder_virtualenv
pip3 install -r requirements.txt
