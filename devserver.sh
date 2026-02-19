#!/bin/sh
source .venv/bin/activate
PORT=${PORT:-8001}
.venv/bin/python myproject/manage.py runserver 0.0.0.0:$PORT
