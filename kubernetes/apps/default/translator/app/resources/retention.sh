#!/bin/sh
set -eu
trap 'exit 0' TERM INT
while true; do
    python -m translator.retention
    sleep 86400 &
    wait "$!"
done
