#!/bin/bash -ec
mariadb-admin status -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}"
