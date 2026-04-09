.PHONY: build serve deploy ssh setup miniflux gitea goatcounter enrich

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

enrich:
	uv run enrich.py
