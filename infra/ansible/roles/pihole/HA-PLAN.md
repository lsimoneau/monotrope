# Pi-hole HA DNS — implementation plan (deferred)

**Status:** deferred until a second physical node is available.
**Why deferred:** the value of HA DNS is surviving the box that DNS lives
on going down (reboots, updates, hardware failure). Two Pi-hole instances
on the *same* OptiPlex only protects against a container/LXC fault, not a
host outage — and the host is exactly what we reboot for Proxmox updates.
So the second instance needs to live on separate hardware.

## The problem this solves

DNS is infrastructure everything else depends on, so it must not have a
single point of failure. The naive "Pi-hole primary + public resolver as
secondary" approach does **not** work: DNS clients treat a resolver list
as load-balanced/parallel, not primary-with-standby. That setup leaks
queries to the public resolver while Pi-hole is up (intermittent ad-block
bypass) and still doesn't fail over cleanly. See the conversation that
spawned this plan — that's why Pi-hole was pulled out of the Archer's DNS
config in the first place.

The correct model is **redundancy at the resolver layer**: two Pi-hole
nodes that *both* filter, fronted by a single floating IP. Clients point
at one address; failover happens at the IP layer, instantly, with no
query leakage.

## Current state (single node)

- One Pi-hole v6 LXC: `pihole` @ 192.168.0.95 (vmid 105), `host` network
  so :53 binds eth0 directly. Upstreams 1.1.1.1 / 9.9.9.9, listening mode
  `all`. Admin UI at `pihole.monotrope.au` via Caddy on Proxmox.
- **Not** currently advertised as LAN DNS — pulled from the Archer because
  v6 failover couldn't be configured (see IPv6 section).
- Infra LXCs (e.g. `apps`) resolve via 1.1.1.1/8.8.8.8 in `/etc/resolv.conf`,
  so they don't depend on Pi-hole today.

## Target architecture

```
        clients (DHCP) ──► VIP 192.168.0.53  (floating, VRRP)
                                │
                 ┌──────────────┴───────────────┐
            pihole  (MASTER)              pihole2 (BACKUP)
        192.168.0.95 / OptiPlex      192.168.0.94 / 2nd node
                 ▲                              ▲
                 └────── nebula-sync ───────────┘
                     (primary → replica, cron)
```

- **VIP `192.168.0.53`** (mnemonic for :53) — owned by whichever node is
  VRRP MASTER. This single address is what clients use; it *is* the HA, so
  no "secondary DNS" is configured anywhere.
- Both nodes run the full filtering stack, so a query answered by either is
  identically blocked — no leak.

## Hardware options for the second node

Pi-hole is light (≤512 MB RAM, negligible CPU). Any of:
- **Raspberry Pi 4/5** — cheapest, fully independent power/hardware. Run
  Pi-hole in Docker the same as the LXC, or bare. Ansible reaches it like
  any other host.
- **Second mini PC** (another OptiPlex Micro / NUC) — overkill for DNS
  alone but doubles as a second Proxmox node for broader HA later.
- **Existing always-on device** (NAS, etc.) if it can run a container and
  bind :53.

Independence from the OptiPlex (separate power especially) is the point.

## Implementation steps

1. **Stand up the second Pi-hole.** Make the `pihole` role instance-aware
   so it deploys to both `pihole` and `pihole2`. Per-host vars: VRRP
   `state` (MASTER/BACKUP), `priority`, interface. Keep both on `host`
   networking. Same upstreams, same listening mode.

2. **keepalived / VRRP.** Run keepalived on both nodes to manage the VIP.
   Two viable shapes, pick one:
   - **Host-network container** alongside Pi-hole (mirrors the existing
     `network_mode: host` + `NET_ADMIN` pattern in `compose.yml.j2`).
   - **Native install** (`apt install keepalived`) on the LXC/host.
   Config: MASTER priority 150 / BACKUP 100, `virtual_ipaddress
   192.168.0.53/24 dev eth0`, advert interval 1s, shared `auth_pass`.
   Add a `vrrp_script` health check that pings Pi-hole's own FTL (e.g.
   `dig @127.0.0.1 +short google.com`) so the VIP also moves on a
   Pi-hole-process failure, not just a node-down.
   - ⚠️ **Verify the LXC can do VRRP**: unprivileged LXCs need `NET_ADMIN`
     to add the VIP alias and must be allowed to send VRRP multicast
     (224.0.0.18, proto 112) on `vmbr0`. Test on a throwaway VIP before
     cutover. If the unprivileged LXC can't, either make the pihole LXCs
     privileged or run keepalived on the Proxmox host(s). Track the needed
     cap/feature in `inventories/home/hosts.yml` like other `lxc_features`.

3. **Config sync — `nebula-sync`.** Pi-hole v6 stores config as
   `pihole.toml` + uses the Teleporter API; classic gravity-sync is v5-era.
   Use **nebula-sync** (v6-native): one container, `PRIMARY` =
   pihole's API URL+password, `REPLICAS` = pihole2, `FULL=true` (or scope
   to gravity/adlists/cname), `CRON` e.g. every 15 min. Run it on the
   primary node or the Proxmox host. New small role or fold into `pihole`.
   - Admin password is already vaulted (`pihole_web_password`); reuse it.

4. **Inventory + vars.** Add `pihole2` host on the new hardware. Add a
   `pihole_ha` group or group_vars carrying `pihole_vip: 192.168.0.53`,
   keepalived auth, per-host priorities. DHCP/MAC reservation for the new
   node at the router per the homelab convention (never static-in-guest).

5. **Validate failover BEFORE pointing clients at it** (see Testing).

6. **Cut clients over (IPv4).** Set the Archer's DHCP DNS to a **single**
   entry: `192.168.0.53`. No secondary. Exclude `.53` from the DHCP pool.
   Renew a client lease and confirm it resolves via the VIP.

7. **Decide internal-LXC resolvers.** Once the VIP is HA, infra LXCs
   (`apps`, etc.) *can* safely point `/etc/resolv.conf` at `192.168.0.53`.
   Trade-off: routing infra DNS through Pi-hole gives blocklist coverage +
   query visibility, but couples them to it. Given the VIP removes the
   SPOF, switching them over is reasonable — but stage it, and watch for
   the Miniflux gotcha below.

## IPv6 — the Archer AX55 limitation (the real blocker)

This is the piece that ties back to "would better hardware fix it?":

- LXCs use `ip6=auto` (SLAAC), so IPv6 clients learn DNS via **RDNSS in
  Router Advertisements**, not DHCPv6 (and Android ignores DHCPv6 anyway).
- The **TP-Link Archer AX55** consumer firmware does not expose a custom
  IPv6 LAN DNS / RDNSS field — it advertises the router itself or the
  ISP-assigned servers. So there's no way to point v6 clients at the
  Pi-hole VIP from the Archer. That's a genuine hardware/firmware ceiling,
  not a misconfiguration.
- **Options to get v6 filtering:**
  1. **Replace the Archer** with a router that controls RDNSS/DHCPv6 DNS —
     OPNsense/pfSense, UniFi, MikroTik, or OpenWrt. Then advertise an IPv6
     VIP (VRRPv3 supports v6) the same way as v4. *This is the clean fix
     and the natural companion hardware upgrade.*
  2. **Take RA over from the Pi-hole nodes** (radvd/dnsmasq advertising the
     VIP) and disable RA-DNS on the Archer. More moving parts, fragile
     alongside consumer firmware — not recommended.
- **Interim (until router upgrade):** v4 is HA-filtered; v6-only lookups
  fall back to router/ISP DNS (minor leak on dual-stack clients, since
  most names resolve over v4 first). Acceptable until the router changes.

So: better hardware *does* resolve the v6 gap — but specifically a
**better router**, alongside the second node for the v4 VIP. A fancier
router alone would never have given "reliable failover to a public
resolver," because that isn't how DNS clients behave.

## Testing / validation

- `dig @192.168.0.53 example.com` resolves from a LAN client.
- Stop Pi-hole on MASTER (or the whole node) → VIP moves to BACKUP within
  ~3s → `dig @192.168.0.53` still resolves. Restart → VIP returns.
- A known-blocked domain returns `0.0.0.0`/NXDOMAIN from **both** nodes
  individually (`dig @192.168.0.95`, `dig @192.168.0.94`) — proves no leak.
- After a blocklist/CNAME change on primary, confirm nebula-sync propagates
  it to the replica within the cron window.
- Failover during a real Proxmox host reboot: DNS stays up the whole time.

## Gotchas

- **Miniflux error-limit trap (learned the hard way):** Miniflux stops
  polling a feed after `POLLING_PARSING_ERROR_LIMIT` (default **3**)
  consecutive failures and silently drops it from the scheduler. A brief
  DNS blip during cutover can permanently sideline feeds until manually
  reset (`UPDATE feeds SET parsing_error_count=0, parsing_error_msg='',
  next_check_at=now() WHERE parsing_error_count>0;`). If pointing `apps`
  at the VIP, do it cleanly and re-check Miniflux after. Consider setting
  `POLLING_PARSING_ERROR_LIMIT=0` in the miniflux role as a hardening.
- **Listening mode `all`** is already set and is required because the
  Archer sources WAN-DNS-forwarder queries from its CGNAT WAN IP. Keep it.
- **Pi-hole v6 config drift:** anything changed via the admin UI on the
  replica will be overwritten by nebula-sync. Treat primary as the source
  of truth; make changes there (or in Ansible).
- **VIP outside DHCP pool:** reserve `.53` so the router never leases it.
```
