#!/bin/bash

# Start mariadb
# https://stackoverflow.com/a/48648098/3549270
mysqld_safe &
sleep 2
until mysqladmin ping -s; do sleep 1; done

# Test all endpoints
/app/.venv/bin/python /app/etc/oparl-test-all/test_all_endpoints.py
