.PHONY: build serve deploy ssh setup miniflux gitea goatcounter hermes hermes-sync hermes-chat enrich

# Load .env if it exists
-include .env
export

DEPLOY_USER := deploy
MONOTROPE_HOST ?=

build: enrich
	cd site && hugo --minify

serve:
	cd site && hugo server --buildDrafts --disableFastRender

deploy:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	bash deploy.sh

ssh:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ssh $(DEPLOY_USER)@$(MONOTROPE_HOST)

setup:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml

miniflux:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags miniflux

gitea:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags gitea

goatcounter:
	@test -n "$(MONOTROPE_HOST)" || (echo "Error: MONOTROPE_HOST is not set"; exit 1)
	ansible-playbook -i "$(MONOTROPE_HOST)," -u root infra/ansible/playbook.yml --tags goatcounter

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
	ssh -t root@$(MONOTROPE_HOST) docker exec -it hermes hermes chat


enrich:
	uv run enrich.py
