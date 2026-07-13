#!/usr/bin/env bash
#
# Managed by Ansible (role: nfs_shutdown_guard). Do not edit by hand.
#
# Why this exists
# ---------------
# The PVE NFS storages are mounted `hard`, deliberately: `soft` trades a hang
# for silent write errors, and the Calibre library and Immich uploads both live
# on there. But a `hard` mount retries a dead server forever, so any unmount
# that touches it blocks in uninterruptible D-state — nothing, not even
# SIGKILL, gets it out.
#
# So if the NAS goes down BEFORE this host — a UPS-triggered shutdown, or
# simply powering the NAS off first — then:
#
#   * pve-guests stops guests one at a time, and each container holding an NFS
#     bind wedges forever on its rootfs umount;
#   * pve-guests.service ships with TimeoutSec=infinity, so nothing ever gives
#     up and the host hangs mid-shutdown until someone holds the power button.
#
# Observed 2026-07-13: a 15-minute hang in which CTs 101-104 were never even
# asked to stop, because CT 106's umount was still blocked ahead of them in the
# queue. See also the TimeoutStopSec drop-in this role installs on pve-guests.
#
# What it does
# ------------
# On a healthy shutdown: nothing whatsoever. The unit is ordered
# After=pve-guests.service, and systemd stops units in the reverse of start
# order, so this ExecStop runs BEFORE pve-guests begins stopping guests — the
# only window in which the deadlock can still be broken. We probe every NFS
# server we have mounted; if they all answer, we exit and the normal graceful
# path proceeds completely untouched.
#
# Only when a server is UNREACHABLE do we act — and at that point a graceful
# stop is no longer achievable at all (the data is already gone), so the only
# question left is whether this host powers off or hangs until morning. For
# that server alone we then:
#
#   1. force-unmount its mounts in EVERY mount namespace, not just the host's.
#      The containers' binds are separate mount instances of the same dead
#      superblock and are invisible to a plain host umount. This is done first
#      because it is what releases processes already stuck in D-state.
#   2. stop the containers that bind it, escalating: a bounded graceful stop,
#      then `lxc-stop -k`, then SIGKILL via the pve-container@ unit. All three
#      rungs are needed — on 2026-07-13 `lxc-stop -k` itself timed out, and
#      even once CT 103's cgroup was completely empty its lxc-start supervisor
#      sat in epoll_wait forever and had to be killed.
#   3. sweep the namespaces once more, to catch binds the dying containers only
#      released on their way out.
#
# It is deliberately incapable of blocking the shutdown it exists to rescue:
# every external command is wrapped in `timeout`, and it always exits 0.
set -euo pipefail

# Tunables (overridden via Environment= in the unit).
probe_port="${NFS_GUARD_PROBE_PORT:-2049}"
probe_timeout="${NFS_GUARD_PROBE_TIMEOUT:-3}"
probe_tries="${NFS_GUARD_PROBE_TRIES:-2}"
stop_grace="${NFS_GUARD_STOP_GRACE:-20}"

log() { echo "nfs-shutdown-guard: $*"; }

# Every NFS mount in a given mounts file, as "<server> <mountpoint>" pairs.
# The device field looks like "192.168.0.49:/volume1/media", so the server is
# everything before the first colon.
nfs_mounts_in() {
  awk '$3 ~ /^nfs4?$/ { split($1, dev, ":"); print dev[1], $2 }' "$1" 2>/dev/null || true
}

# Liveness probe. A powered-off NAS on the same LAN usually fails fast
# (EHOSTUNREACH, no ARP reply), but a blackholed one just goes quiet — hence
# the explicit timeout rather than relying on the connect() default.
server_alive() {
  local server=$1 attempt
  for ((attempt = 1; attempt <= probe_tries; attempt++)); do
    if timeout "$probe_timeout" \
      bash -c "exec 3<>/dev/tcp/${server}/${probe_port}" 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

# Force+lazy unmount every mount of $1 in every mount namespace on the box.
# Namespaces are deduplicated by their ns inode: dozens of processes share a
# container's namespace, and unmounting once per process would be pointless.
sweep_namespaces() {
  local server=$1
  local -A seen_ns=()
  local mounts_file pid ns mountpoint

  for mounts_file in /proc/[0-9]*/mounts; do
    pid=${mounts_file#/proc/}
    pid=${pid%/mounts}

    ns=$(readlink "/proc/${pid}/ns/mnt" 2>/dev/null || true)
    [ -n "$ns" ] || continue
    [ -z "${seen_ns[$ns]:-}" ] || continue
    seen_ns[$ns]=1

    while read -r mount_server mountpoint; do
      [ "$mount_server" = "$server" ] || continue
      if timeout 10 nsenter -t "$pid" -m -- \
        umount -f -l "$mountpoint" >/dev/null 2>&1; then
        log "unmounted ${mountpoint} (mount ns of pid ${pid})"
      fi
    done < <(nfs_mounts_in "$mounts_file")
  done
}

# Stop a container that can no longer stop gracefully, escalating only as far
# as it has to.
force_stop_ct() {
  local id=$1

  ct_running() {
    timeout 5 lxc-info -n "$id" -s 2>/dev/null | grep -q RUNNING
  }

  ct_running || return 0

  log "CT ${id} binds a dead NFS mount; a graceful stop cannot complete — stopping it now"
  timeout "$((stop_grace + 5))" lxc-stop -n "$id" -t "$stop_grace" >/dev/null 2>&1 || true

  if ct_running; then
    log "CT ${id} ignored the graceful stop; killing it"
    timeout 15 lxc-stop -n "$id" -k >/dev/null 2>&1 || true
  fi

  if ct_running; then
    # Its cgroup may already be empty while lxc-start sits in epoll_wait,
    # never noticing its init died. SIGKILL the whole unit cgroup.
    log "CT ${id} still RUNNING; SIGKILLing pve-container@${id}.service"
    timeout 10 systemctl kill --signal=SIGKILL "pve-container@${id}.service" >/dev/null 2>&1 || true
  fi
}

# Containers whose rootfs or any mountpoint entry sits under $1.
cts_binding() {
  local mountpoint=$1 conf id
  for conf in /etc/pve/lxc/*.conf; do
    [ -e "$conf" ] || continue
    id=$(basename "$conf" .conf)
    if grep -qE "^(rootfs|mp[0-9]+):[[:space:]]*${mountpoint}[,/]" "$conf" 2>/dev/null; then
      echo "$id"
    fi
  done
}

main() {
  mapfile -t mounts < <(nfs_mounts_in /proc/mounts)
  if [ "${#mounts[@]}" -eq 0 ]; then
    log "no NFS mounts on this host; nothing to do"
    return 0
  fi

  mapfile -t servers < <(printf '%s\n' "${mounts[@]}" | awk '{print $1}' | sort -u)

  local dead=() server
  for server in "${servers[@]}"; do
    if server_alive "$server"; then
      log "NFS server ${server} is reachable"
    else
      log "NFS server ${server} is UNREACHABLE"
      dead+=("$server")
    fi
  done

  if [ "${#dead[@]}" -eq 0 ]; then
    log "all NFS servers reachable; leaving the graceful shutdown path alone"
    return 0
  fi

  local mountpoints id
  for server in "${dead[@]}"; do
    log "rescuing shutdown: NFS server ${server} is gone, its mounts can never be unmounted cleanly"

    mapfile -t mountpoints < <(
      printf '%s\n' "${mounts[@]}" | awk -v s="$server" '$1 == s { print $2 }'
    )

    # 1. Release anything already blocked in D-state on the dead server.
    sweep_namespaces "$server"

    # 2. Stop the containers that depend on it.
    for mountpoint in "${mountpoints[@]}"; do
      while read -r id; do
        [ -n "$id" ] || continue
        force_stop_ct "$id"
      done < <(cts_binding "$mountpoint")
    done

    # 3. Catch binds released only as the containers died.
    sweep_namespaces "$server"

    for mountpoint in "${mountpoints[@]}"; do
      if timeout 10 umount -f -l "$mountpoint" >/dev/null 2>&1; then
        log "unmounted host mount ${mountpoint}"
      fi
    done

    log "rescue complete for ${server}; handing back to the normal shutdown"
  done
}

main "$@" || log "rescue hit an error; continuing so the shutdown is never blocked"
exit 0
