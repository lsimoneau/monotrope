#!/usr/bin/env bash
#
# Managed by Ansible (role: nfs_container_guard). Do not edit by hand.
#
# Why this exists
# ---------------
# After a power outage the NAS and this LXC's host boot together. For a short
# window the NFS mount denies the container-root uid (idmap 0 -> 100000, which
# the NAS squashes to nobody). Docker's boot-time auto-start of containers
# whose bind sources are SUBDIRECTORIES of the NFS mount (e.g. /library/books)
# then fails its create-time `mkdir` check with EACCES. Because that is a
# mount/create error and not a runtime crash, the `unless-stopped` restart
# policy never retries it, so the container stays Exited(255) even after NFS
# has fully recovered. (Containers that bind the mount ROOT are immune: Docker
# only stats a local mountpoint that always exists, so they are out of scope.)
#
# What it does
# ------------
# Run on a timer. First PROBE every configured bind-source path the same way
# Docker does (mkdir -p + confirm it is a directory); if any is not ready we
# exit non-zero so the failure is visible in journald/`systemctl` rather than
# silently swallowed, and try again on the next tick. Only once every path is
# healthy do we RECONCILE: (re)start any container that is `exited` with an
# `unless-stopped`/`always` policy. Being policy-driven, it needs no
# per-container allowlist and is a harmless no-op once everything is up.
#
# It only ever ACTS after the mount is confirmed usable, so it completes a
# deferred start — it never forces a container into a genuinely broken mount.
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "nfs-container-guard: no bind-source paths given" >&2
  exit 2
fi

# 0. Liveness gate. The probe below is a WRITE to an NFS path, and the mounts
#    are `hard` — so if the NAS is unreachable, `mkdir` does not fail, it parks
#    in uninterruptible D-state forever and takes this unit (and, at shutdown,
#    the container stopping it) down with it. Seen on 2026-07-13: a shutdown
#    with the NAS already off left `mkdir -p /library/books` unkillable.
#    So: never touch the mount until we know someone is listening. A dead
#    server is not an error worth alarming on — it means the NAS is down, which
#    is a fact about the NAS, not about the containers we reconcile — so we
#    exit 0 quietly and try again on the next tick.
nfs_server_for() {
  # Longest mountpoint prefix of $1 that is an NFS mount → its server.
  awk -v path="$1" '
    $3 ~ /^nfs4?$/ && index(path "/", $2 == "/" ? "/" : $2 "/") == 1 {
      if (length($2) > length(best_mp)) { best_mp = $2; split($1, dev, ":"); best = dev[1] }
    }
    END { if (best != "") print best }
  ' /proc/mounts 2>/dev/null || true
}

for p in "$@"; do
  server=$(nfs_server_for "$p")
  [ -n "$server" ] || continue
  if ! timeout 3 bash -c "exec 3<>/dev/tcp/${server}/2049" 2>/dev/null; then
    echo "nfs-container-guard: NFS server ${server} (serving '$p') is unreachable; skipping probe so we don't block on a hard mount"
    exit 0
  fi
done

# 1. Probe: replicate Docker's create-time bind-source check. `timeout` is a
#    second line of defence only — it cannot interrupt a D-state mkdir, but it
#    does stop us waiting on one if the server dies between the gate above and
#    here.
for p in "$@"; do
  if ! timeout 30 mkdir -p "$p" 2>/dev/null || [ ! -d "$p" ]; then
    echo "nfs-container-guard: bind source '$p' not ready (NFS settling or unhealthy); retry next tick" >&2
    exit 1
  fi
done

# 2. Reconcile: (re)start containers Docker was meant to keep running but that
#    are down with a recorded error. The discriminator is a non-empty
#    .State.Error: a failed start/restart records one (both the "created" fresh
#    failure, exit 128, and the "exited" restart failure, exit 137/255), whereas
#    a deliberate `docker stop` of an unless-stopped container leaves it empty.
#    Keying on it means we complete a failed start without ever overriding a
#    manual stop. Exit codes alone can't tell them apart (137 occurs in both).
started=0
for c in $(docker ps -aq); do
  running=$(docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null || echo true)
  [ "$running" = "false" ] || continue

  policy=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$c" 2>/dev/null || true)
  case "$policy" in
    unless-stopped | always) ;;
    *) continue ;;
  esac

  err=$(docker inspect -f '{{.State.Error}}' "$c" 2>/dev/null || true)
  [ -n "$err" ] || continue

  name=$(docker inspect -f '{{.Name}}' "$c" 2>/dev/null | sed 's#^/##')
  if docker start "$c" >/dev/null 2>&1; then
    echo "nfs-container-guard: started stuck container '$name' (policy=$policy, prior error: $err)"
    started=$((started + 1))
  else
    echo "nfs-container-guard: FAILED to start '$name' (policy=$policy, error: $err)" >&2
  fi
done

if [ "$started" -gt 0 ]; then
  echo "nfs-container-guard: reconciled $started container(s)"
fi
