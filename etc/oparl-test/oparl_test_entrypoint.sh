#!/bin/bash

# Start mariadb
# https://stackoverflow.com/a/48648098/3549270
mysqld_safe &
sleep 2
until mysqladmin ping -s; do sleep 1; done

# Run the import
/app/.venv/bin/python /app/manage.py import --skip-body-extra $1
