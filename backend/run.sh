#!/bin/bash
set -e

cd /home/student/ejicodeai
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
