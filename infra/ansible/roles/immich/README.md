# immich

Self-hosted photo library — phone auto-backup, timeline, albums, shared
albums, and optional ML (face detection + CLIP semantic search). Runs on its
own LXC (`immich`, vmid 106) because Immich wants 4–6 GB RAM and the apps LXC
is capped at 2 GB.

- **Web:** `photos.monotrope.au` (Caddy → `192.168.0.90:2283`)
- **Originals:** NAS via NFS at `/library/photos` (`/volume1/library/photos`)
- **Database / Redis / model cache:** LXC local rootfs (NFS is unsupported for
  the DB)

## Architecture notes

- Immich runs its containers as root; our NAS export is `root_squash`, so
  container-root → `nobody` → `EACCES` on `/library/photos`. The official
  Immich image ignores PUID/PGID, so we run `immich-server` via the compose
  **`user: "1028:1028"`** directive (the NAS `homelab` user), which the LXC's
  `nas_idmap` feature identity-maps into the container. This is why the photo
  dir must be owned by `1028:1028`.
- `immich-server` bind-mounts a **subdirectory** of the NFS mount, so it's
  subject to the post-boot NFS race — the `nfs_container_guard` role runs on
  this LXC with `nfs_guard_paths: [/library/photos]`.
- Photo **originals are NOT in restic** (restic only covers LXC rootfs). They
  rely on the NAS's own backup/snapshots. Only the Postgres DB is dumped to
  Wasabi (see `restic_backup` — set `immich-db`).

## One-time provisioning (not Ansible-managed)

### 1. Create the photo directory on the NAS (as the homelab user, uid 1028)

```sh
ssh homelab@192.168.0.49 'mkdir -p /volume1/library/photos'
# confirm ownership is 1028:1028
```

### 2. Create the LXC on the Proxmox host (pve)

```sh
# Use the same Debian template as the other LXCs (pveam list local).
pct create 106 local:vztmpl/<debian-standard>.tar.zst \
  --hostname immich \
  --cores 4 --memory 6144 --swap 2048 \
  --rootfs local-lvm:32 \
  --net0 name=eth0,bridge=vmbr0,firewall=1,ip=dhcp,ip6=auto,type=veth \
  --features nesting=1 \
  --onboot 1 --startup order=4,up=30 \
  --unprivileged 1 --ostype debian
# NAS library bind mount (same Proxmox storage the apps LXC uses):
pct set 106 -mp0 /mnt/pve/library,mp=/library
pct start 106
```

Do **not** set `lxc.idmap` / tun by hand — `proxmox_lxc_config` renders those
from `lxc_features: [tun, nas_idmap]` and reboots the container on first apply.

### 3. Reserve the IP

Get the MAC (`pct config 106 | grep net0`), add a DHCP reservation at the
router pinning it to **192.168.0.90**, then confirm `ansible_host` in
`inventories/home/hosts.yml` matches.

### 4. Add the DB password to the vault

Load the `ansible-vault` skill, then:

```sh
.agents/skills/ansible-vault/scripts/vault-add.sh vault_immich_db_password
ansible-vault edit group_vars/all/vault.yml   # set an ALPHANUMERIC-ONLY value
```

### 5. Deploy

```sh
make home LIMIT=immich          # or: make home LIMIT=pve,immich
```

`pve` is needed once to render the host-side idmap (LXC conf) and the Caddy
vhost.

## After first deploy

1. Open `https://photos.monotrope.au`, create the admin account.
2. **Admin → Settings → Job Settings:** set *Smart Search* and *Face
   Detection* concurrency to **1** before the first big import so ML doesn't
   push the node into swap. Raise later once steady-state.
3. Install the Immich mobile app on both phones (with Tailscale for off-LAN
   background upload), point it at `https://photos.monotrope.au`, enable
   backup.
4. Lightroom workflow: your partner downloads originals from the web UI /
   shared albums (RAW + JPEG are preserved byte-for-byte).

## Restore (DB)

Originals restore from the NAS backup. For the database, restore the latest
`immich_dump.sql` from restic into a fresh stack, e.g.:

```sh
cat immich_dump.sql | docker exec -i immich-database-1 psql -U immich -d immich
```

Verify the exact restore procedure against the current Immich backup docs —
the VectorChord/pgvector extension handling can change between versions.
