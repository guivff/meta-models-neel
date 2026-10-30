#!/bin/bash
set -eu
D=/private/tmp/activation-readers-global-deploy.lock
case "$1" in
 acquire) for i in $(seq 1 55); do if mkdir "$D" 2>/dev/null; then printf '%s' "$2" > "$D/owner"; exit 0; fi; sleep 1; done; exit 1;;
 release) test "$(cat "$D/owner")" = "$2"; rm "$D/owner"; rmdir "$D";;
 *) exit 2;;
esac
