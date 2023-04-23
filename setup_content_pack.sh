#!/usr/bin/env bash
python3 -m venv pyenv
source pyenv/bin/activate
pip install --require-virtualenv -r requirements.txt > /dev/null
python3 install_content_pack.py
deactivate
