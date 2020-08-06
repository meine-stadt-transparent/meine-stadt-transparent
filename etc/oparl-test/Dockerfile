FROM konstin2/meine-stadt-transparent

ENV ENV_PATH etc/oparl-test/oparl-test.env

# sqlite3 leads to undebuggable "database is locked errors", and since
# I want to ship this as a single docker container, I install mariadb
# in this docker container with dummy authentication

# We need the root user to start mariadb later
USER root
RUN apt update && apt-get install -y mariadb-server

# https://stackoverflow.com/a/48648098/3549270
RUN mysqld_safe & until mysqladmin ping; do sleep 1; done && \
    mysql -e "SET PASSWORD FOR 'root'@'localhost' = PASSWORD('dummy'); FLUSH PRIVILEGES" && \
    mysql -uroot -pdummy -e "CREATE DATABASE mst_oparl_test;" && \
    /app/.venv/bin/python /app/manage.py migrate

ENTRYPOINT ["/app/etc/oparl-test/oparl_test_entrypoint.sh"]
