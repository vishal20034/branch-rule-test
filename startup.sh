#!/bin/bash
set -e
cd /home/site/wwwroot
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
exec gunicorn --bind=0.0.0.0:8000 app:app
