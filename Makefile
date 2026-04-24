.PHONY: build serve deploy ssh setup infra logs miniflux gitea goatcounter hermes hermes-sync hermes-chat hermes-cli enrich wireguard calibre calibre-build calibre-sync koinsight wallabag obsidian obsidian-login

# Load .env if it exists
-include .env
export

DEPLOY_USER := deploy
MONOTROPE_HOST ?=

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
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml

logs:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh -t root@$(MONOTROPE_HOST) mlogs $(ARGS)

miniflux:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags miniflux

gitea:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags gitea

goatcounter:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags goatcounter

obsidian:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags obsidian

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
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags hermes

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
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags wireguard

calibre-build:
	docker build -t git.monotrope.au/louis/calibre-web:latest infra/calibre/
	docker push git.monotrope.au/louis/calibre-web:latest

calibre: calibre-build
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags calibre

calibre-sync:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh root@$(MONOTROPE_HOST) /opt/calibre/sync.sh

koinsight:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags koinsight

wallabag:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags wallabag

enrich:
	uv run enrich.py
