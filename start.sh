#!/usr/bin/env bash
python3 -m venv pyenv
source pyenv/bin/activate
pip install --require-virtualenv -r requirements.txt > /dev/null
printf "Now you may use setup_graylog.py script in python venv (pyenv)\n"
printf "To do this -> source pyenv/bin/activate or source this script\n"
printf "You can then use ./setup_graylog.py. Check it's options with -h\n"
