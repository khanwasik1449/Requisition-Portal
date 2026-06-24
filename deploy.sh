#!/bin/bash
# Production deploy script — called by Jenkins or manually
set -e

APP_DIR=/root/requisition_portal
VENV_DIR=$APP_DIR/venv

cd $APP_DIR

# Pull latest
git pull origin main

# Activate venv
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r $APP_DIR/requirements.txt

# Django steps
cd $APP_DIR
python3 manage.py migrate
python3 manage.py collectstatic --noinput
python3 manage.py check

# Restart
sudo systemctl restart requisition_portal.service
echo "Deploy complete."
