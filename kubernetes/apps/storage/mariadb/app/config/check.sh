#!/bin/bash -ec
mysqladmin status -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}"
