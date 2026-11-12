#!/bin/sh
set -eu
# Initialize ephemeral storage on Free, or a mounted disk on a paid service.
mkdir -p /data/socialmonitor
chown speculara:speculara /data /data/socialmonitor
exec setpriv --reuid=10001 --regid=10001 --init-groups /bin/sh /srv/entrypoint.sh
