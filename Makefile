.PHONY: build serve deploy ssh setup infra logs miniflux goatcounter hermes hermes-sync hermes-chat hermes-cli enrich wireguard calibre calibre-sync koinsight wallabag obsidian obsidian-login backup-setup backup

DEPLOY_USER := deploy

# Read the VPS host from its inventory (single source of truth — Ansible
# uses the same file at runtime via -i below).
VPS_INVENTORY := infra/ansible/inventories/vps/hosts.yml
MONOTROPE_HOST := $(shell awk -F': *' '/ansible_host:/ {gsub(/[" ]/, "", $$2); print $$2}' $(VPS_INVENTORY))

# ansible-playbook picks this up automatically; covers all targets below.
ANSIBLE_VAULT_PASSWORD_FILE := .vault_pass

export MONOTROPE_HOST DEPLOY_USER ANSIBLE_VAULT_PASSWORD_FILE

build:
	cd site && hugo --minify

serve:
	cd site && hugo server --buildDrafts --disableFastRender

deploy:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	bash deploy.sh

ssh:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh $(DEPLOY_USER)@$(MONOTROPE_HOST)

setup infra:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml

logs:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh -t root@$(MONOTROPE_HOST) mlogs $(ARGS)

miniflux:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags miniflux

goatcounter:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags goatcounter

obsidian:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags obsidian

# Re-authenticate the headless Obsidian Sync client.
# Run when sync starts logging "Failed to authenticate: Not logged in".
# Override the email by passing EMAIL=... on the command line.
OBSIDIAN_EMAIL ?= simoneau.louis@gmail.com
obsidian-login:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh -t root@$(MONOTROPE_HOST) docker exec -it obsidian-sync ob login --email $(OBSIDIAN_EMAIL)
	ssh root@$(MONOTROPE_HOST) docker restart obsidian-sync

hermes: hermes-sync
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags hermes

hermes-sync:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	@echo "Checking for remote config changes..."
	@ssh root@$(MONOTROPE_HOST) docker cp hermes:/opt/data/config.yaml - 2>/dev/null | tar -xO > /tmp/hermes-remote-config.yaml || true
	@if ! diff -q infra/hermes/config.yaml /tmp/hermes-remote-config.yaml >/dev/null 2>&1; then \
		echo ""; \
		echo "Remote config.yaml differs from local:"; \
		echo "─────────────────────────────────────"; \
		diff -u infra/hermes/config.yaml /tmp/hermes-remote-config.yaml || true; \
		echo "─────────────────────────────────────"; \
		echo ""; \
		read -p "Overwrite remote with local? [y/N] " ans; \
		if [ "$$ans" != "y" ] && [ "$$ans" != "Y" ]; then \
			echo "Aborting. Merge remote changes into infra/hermes/config.yaml first."; \
			exit 1; \
		fi; \
	else \
		echo "Config in sync."; \
	fi

hermes-chat:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh -t root@$(MONOTROPE_HOST) "docker exec -it -u 10000 hermes bash -c '. /opt/hermes/.venv/bin/activate && hermes chat'"

hermes-cli:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh -t root@$(MONOTROPE_HOST) "docker exec -it -u 10000 hermes bash -c '. /opt/hermes/.venv/bin/activate && hermes $(ARGS)'"


wireguard:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags wireguard

calibre:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags calibre

calibre-sync:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh root@$(MONOTROPE_HOST) /opt/calibre/sync.sh

koinsight:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags koinsight

wallabag:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags wallabag

enrich:
	uv run enrich.py

backup-setup:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i $(VPS_INVENTORY) infra/ansible/vps.yml --tags backup

backup:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh root@$(MONOTROPE_HOST) /usr/local/bin/monotrope-backup $(LABEL)
