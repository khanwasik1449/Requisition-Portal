#!/bin/bash
cd "$(dirname "$0")"
export $(grep -v '^#' .env | xargs)
exec gunicorn requisition_portal.wsgi:application --bind 127.0.0.1:8001 --workers 3 --timeout 120 --access-logfile /var/log/requisition_portal/access.log --error-logfile /var/log/requisition_portal/error.log
