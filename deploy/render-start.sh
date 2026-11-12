#!/bin/sh
set -eu
# Render mounts an initially root-owned disk; initialize only these app folders.
mkdir -p /data/socialmonitor
chown speculara:speculara /data /data/socialmonitor
exec setpriv --reuid=10001 --regid=10001 --init-groups /bin/sh /srv/entrypoint.sh
