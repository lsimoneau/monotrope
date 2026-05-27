# Backup Strategy

Centralised restic backup from the Proxmox host (`pve`) to Wasabi S3
(`s3.ap-southeast-2.wasabisys.com/monotrope-backup/restic`).

## Architecture

- **Where it runs**: Proxmox host (`pve`, 192.168.0.59) — single credential
  deployment, single systemd timer.
- **How it accesses LXC data**: `pct mount <vmid>` exposes each container's
  rootfs at `/var/lib/lxc/<vmid>/rootfs/`. The script mounts before backup and
  unmounts after (including on failure via a trap).
- **Repository**: restic repo on Wasabi S3, initialised automatically by
  Ansible on first deploy. Content-addressed deduplication means identical
  chunks across backup sets are stored once.
- **Credentials**: `/usr/local/bin/restic-backup.env` on pve (0600, root only).
  Sourced with `set -a` to export to restic. Wasabi keys and restic password
  come from the Ansible vault (`vault_backup_wasabi_*`, `vault_restic_password`).
- **Ansible role**: `infra/ansible/roles/restic_backup/`. All backup config is
  in `defaults/main.yml`. Deploy with `make home LIMIT=pve`.

## Schedule and retention

| Setting | Value |
|---|---|
| Timer | Daily at 03:00 with up to 15 min random jitter |
| Daily snapshots | 30 |
| Weekly snapshots | 12 |
| Monthly snapshots | 12 |

Timer: `restic-backup.timer` on pve. Logs: `journalctl -u restic-backup`.

## Backup process

The script (`/usr/local/bin/restic-backup.sh`) runs four phases:

1. **Mount** — `pct mount` for each LXC (103, 104, 102, 101, 105)
2. **Pre-backup hooks** — database dumps (currently Miniflux PostgreSQL only)
3. **Backup** — one `restic backup` invocation per set, tagged by name and
   priority. Files are read directly from the LXC rootfs mount points.
4. **Forget + prune** — applies retention policy and removes unreferenced data

On exit (success or failure), the cleanup trap unmounts all LXCs and removes
temp files.

## Backup sets

### Priority 1 — Critical (irreplaceable, interactive auth required to recreate)

#### miniflux-db (apps LXC 103)

Pre-backup: `pg_dump -U miniflux miniflux -F c` piped to
`/var/tmp/restic-dumps/miniflux_dump.pgdump` on the host.

| Path | Contents |
|---|---|
| `var/lib/docker/volumes/miniflux_miniflux_db/_data` | PostgreSQL data dir |
| `/var/tmp/restic-dumps/miniflux_dump.pgdump` | Consistent custom-format dump |

Tags: `miniflux`, `critical`, `apps`

#### hermes-state (hermes LXC 104)

| Path | Contents |
|---|---|
| `root/.hermes` | Entire Hermes home: `config.yaml` (API keys, channel config), `state.db` (memories, sessions), `state-snapshots/` (nightly snapshots), `skills/` (evolved skills), `plugins/` (Miniflux plugin) |

Tags: `hermes`, `critical`

#### audible-ingest (apps LXC 103)

| Path | Contents |
|---|---|
| `var/lib/docker/volumes/audible-ingest_audible_config/_data` | `audible-cli` auth tokens (interactive Audible login) |
| `var/lib/docker/volumes/audible-ingest_audible_state/_data` | `state.json` — which books have been ingested |

Tags: `audible-ingest`, `critical`, `apps`

#### kobo-ingest (apps LXC 103)

| Path | Contents |
|---|---|
| `var/lib/docker/volumes/calibre_kobodl_config/_data` | `kobodl` auth tokens (interactive Kobo store login) |
| `var/lib/docker/volumes/calibre_kobo_ingest_state/_data` | `pinned.json` and ingest state |

Tags: `kobo-ingest`, `critical`, `apps`

### Priority 2 — Important (effort to recreate)

#### audiobookshelf (apps LXC 103)

| Path | Contents |
|---|---|
| `var/lib/docker/volumes/audiobookshelf_config/_data` | Users, libraries, server config |
| `var/lib/docker/volumes/audiobookshelf_metadata/_data` | Listening progress, bookmarks, metadata |

Audiobook files live on the NAS (`/library/audiobooks`), not backed up here.

Tags: `audiobookshelf`, `apps`

#### karakeep (apps LXC 103)

| Path | Contents |
|---|---|
| `var/lib/docker/volumes/karakeep_karakeep_data/_data` | Bookmarks, lists, user data |
| `var/lib/docker/volumes/karakeep_karakeep_meilisearch/_data` | Search index (rebuildable but saves time) |

Tags: `karakeep`, `apps`

#### calibre-web (apps LXC 103)

| Path | Contents |
|---|---|
| `var/lib/docker/volumes/calibre_calibre_config/_data` | Calibre-web settings, conversion profiles |
| `var/lib/docker/volumes/calibre_cwa_ingest/_data` | Book ingestion folder state |

Book library lives on the NAS (`/library/books`), not backed up here.

Tags: `calibre`, `apps`

#### media-stack-configs (media-stack LXC 102)

| Path | Contents |
|---|---|
| `opt/media-stack/gluetun` | VPN config, port-forwarding state |
| `opt/media-stack/qbittorrent` | Torrent client config, categories, RSS rules |
| `opt/media-stack/sonarr` | TV series DB, quality profiles, download history |
| `opt/media-stack/radarr` | Movie DB, quality profiles, download history |
| `opt/media-stack/lidarr` | Music DB, quality profiles |
| `opt/media-stack/prowlarr` | Indexer config, API keys |

Media files live on the NAS (`/data`), not backed up here.

Tags: `media-stack`

#### jellyfin-config (jellyfin LXC 101)

| Path | Contents |
|---|---|
| `var/lib/jellyfin` | Users, watch history, library metadata |
| `etc/jellyfin` | Server config, network settings, API keys |

Excludes: `var/lib/jellyfin/transcodes`, `var/cache/jellyfin`.

Tags: `jellyfin`

### Priority 3 — Nice to have

#### koinsight (apps LXC 103)

| Path | Contents |
|---|---|
| `var/lib/docker/volumes/koinsight_data/_data` | KOReader reading statistics (re-uploaded from Kobo periodically) |

Tags: `koinsight`, `apps`

#### pihole (pihole LXC 105)

| Path | Contents |
|---|---|
| `opt/pihole/etc-pihole` | DNS blocklists, local DNS records, gravity DB, DHCP config |

Tags: `pihole`

### Not backed up

| What | Why |
|---|---|
| Media files (NAS `/data`) | Too large for S3; NAS is separate infrastructure |
| Book library (NAS `/library/`) | Same — NAS responsibility |
| Docker images | Pullable from registries; Ansible rebuilds them |
| ops-broker (`/opt/ops-broker/`) | Fully Ansible-managed, no user state |
| Caddy config (`/etc/caddy/`) | Ansible-managed, re-rendered on deploy |
| Hermes code checkout (`/usr/local/lib/hermes-agent/`) | Git clone, version-pinned in Ansible |

## Monitoring

### Check last backup status

```bash
ssh root@pve 'systemctl status restic-backup'
```

### View backup log

```bash
ssh root@pve 'journalctl -u restic-backup --no-pager'
```

### List snapshots

```bash
ssh root@pve 'set -a; source /usr/local/bin/restic-backup.env; set +a; restic snapshots'
```

### List snapshots for a specific set

```bash
ssh root@pve 'set -a; source /usr/local/bin/restic-backup.env; set +a; restic snapshots --tag miniflux-db'
```

### Check repo stats

```bash
ssh root@pve 'set -a; source /usr/local/bin/restic-backup.env; set +a; restic stats'
```

### Manual run (does not affect the timer schedule)

```bash
ssh root@pve 'systemctl start restic-backup'
```

### Dry run (shows what would be backed up without uploading)

```bash
ssh root@pve '/usr/local/bin/restic-backup.sh --dry-run'
```

## Restore procedures

All restore commands run on `pve`. Set up the restic environment first:

```bash
set -a; source /usr/local/bin/restic-backup.env; set +a
```

### Finding the right snapshot

```bash
# List all snapshots for a tag
restic snapshots --tag <set-name>

# List files in a specific snapshot
restic ls <snapshot-id>
```

### Restoring Docker volumes (general pattern)

For any service backed by Docker named volumes:

```bash
# 1. Find the snapshot
restic snapshots --tag <set-name>

# 2. Stop the container(s)
pct exec 103 -- docker compose -f /opt/<service-dir>/compose.yml down

# 3. Restore files to a temp directory on the host
restic restore <snapshot-id> --target /tmp/restore --include /var/lib/lxc/103/rootfs/var/lib/docker/volumes/<volume-name>/_data

# 4. Copy restored files back into the volume
#    (the volume path on the host rootfs is the same as the backed-up path)
rsync -a --delete /tmp/restore/var/lib/lxc/103/rootfs/var/lib/docker/volumes/<volume-name>/_data/ /var/lib/lxc/103/rootfs/var/lib/docker/volumes/<volume-name>/_data/

# 5. Clean up and restart
rm -rf /tmp/restore
pct exec 103 -- docker compose -f /opt/<service-dir>/compose.yml up -d
```

### Restoring Miniflux (PostgreSQL)

Miniflux uses PostgreSQL and requires a database-level restore from the
`pg_dump`, not file-level restore.

```bash
# 1. Find the snapshot
restic snapshots --tag miniflux-db

# 2. Extract the pg_dump from the snapshot
restic dump <snapshot-id> /var/tmp/restic-dumps/miniflux_dump.pgdump > /tmp/miniflux_restore.pgdump

# 3. Copy the dump into the LXC, then into the container
pct push 103 /tmp/miniflux_restore.pgdump /tmp/miniflux_restore.pgdump
pct exec 103 -- docker cp /tmp/miniflux_restore.pgdump miniflux-db-1:/tmp/miniflux_restore.pgdump

# 4. Option A: In-place restore (keeps DB running, may warn on constraints)
pct exec 103 -- docker exec miniflux-db-1 pg_restore -U miniflux -d miniflux --clean --if-exists /tmp/miniflux_restore.pgdump

# 4. Option B: Full clean restore (stops Miniflux, drops schema, restores everything)
pct exec 103 -- docker stop miniflux-miniflux-1
pct exec 103 -- docker exec miniflux-db-1 psql -U miniflux -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
pct exec 103 -- docker exec miniflux-db-1 pg_restore -U miniflux -d miniflux /tmp/miniflux_restore.pgdump
pct exec 103 -- docker start miniflux-miniflux-1

# 5. Clean up
pct exec 103 -- docker exec miniflux-db-1 rm /tmp/miniflux_restore.pgdump
pct exec 103 -- rm /tmp/miniflux_restore.pgdump
```

### Restoring Hermes state

```bash
# 1. Find the snapshot
restic snapshots --tag hermes-state

# 2. Stop Hermes
pct exec 104 -- systemctl stop hermes-gateway

# 3. Restore to temp dir
restic restore <snapshot-id> --target /tmp/restore --include /var/lib/lxc/104/rootfs/root/.hermes

# 4. Copy back
rsync -a --delete /tmp/restore/var/lib/lxc/104/rootfs/root/.hermes/ /var/lib/lxc/104/rootfs/root/.hermes/

# 5. Clean up and restart
rm -rf /tmp/restore
pct exec 104 -- systemctl start hermes-gateway
```

### Restoring native services (Jellyfin, Pi-hole)

Same pattern — stop the service, restore files, start it back up.

```bash
# Jellyfin example
pct exec 101 -- systemctl stop jellyfin
restic restore <snapshot-id> --target /tmp/restore --include /var/lib/lxc/101/rootfs/var/lib/jellyfin --include /var/lib/lxc/101/rootfs/etc/jellyfin
rsync -a /tmp/restore/var/lib/lxc/101/rootfs/var/lib/jellyfin/ /var/lib/lxc/101/rootfs/var/lib/jellyfin/
rsync -a /tmp/restore/var/lib/lxc/101/rootfs/etc/jellyfin/ /var/lib/lxc/101/rootfs/etc/jellyfin/
rm -rf /tmp/restore
pct exec 101 -- systemctl start jellyfin
```

## Verification checklist

After any restore, verify:

- [ ] Service starts without errors (`systemctl status` or `docker compose ps`)
- [ ] Service logs are clean (`journalctl -u <service>` or `docker logs`)
- [ ] Data is present (log in to the web UI, check recent items exist)
- [ ] Functionality works (add/edit/delete something, confirm it persists)

For a full end-to-end verification (recommended after initial setup or major
changes):

1. Mark some items unread in Miniflux
2. Run a backup: `ssh root@pve 'systemctl start restic-backup'`
3. Mark the items read
4. Follow the Miniflux restore procedure above
5. Confirm the items are unread again

## Modifying the backup config

All backup sets are defined in `infra/ansible/roles/restic_backup/defaults/main.yml`.

To add a new backup set, append to `restic_backup_sets`:

```yaml
- name: my-new-service
  vmid: 103
  paths:
    - var/lib/docker/volumes/my_service_data/_data
  tags: [my-service, apps]
```

To add a database dump before backup, use `pre_commands`:

```yaml
pre_commands:
  - "pct exec 103 -- docker exec my-db pg_dump -U user dbname -F c > {{ restic_dump_dir }}/my_dump.pgdump"
host_paths:
  - "{{ restic_dump_dir }}/my_dump.pgdump"
```

After changes, deploy: `make home LIMIT=pve`.
