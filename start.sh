#!/usr/bin/env bash
python3 -m venv pyenv
source pyenv/bin/activate
pip install --require-virtualenv -r requirements.txt &> /dev/null
if [ "$?" != "0" ]; then
  printf "Installing requirements failed"
  exit 2
fi
if [ "$0" = "$BASH_SOURCE" ]; then
  if [ -n "$1" ]; then
    ./setup_graylog.py "$@"
  elif [ -n "$ELEMENTS" ]; then
    ./setup_graylog.py $ELEMENTS
  else
    printf "Didn't supply root element names\n"
    exit 2
  fi
fi
