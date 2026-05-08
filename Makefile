.PHONY: build serve enrich home

ANSIBLE_VAULT_PASSWORD_FILE := .vault_pass
HOME_INVENTORY := infra/ansible/inventories/home

export ANSIBLE_VAULT_PASSWORD_FILE

# Hugo is built and deployed by Cloudflare Pages on push to main; these
# targets are for local preview only.
build:
	cd site && hugo --minify

serve:
	cd site && hugo server --buildDrafts --disableFastRender

# Enrich book reviews with ISBN + cover from OpenLibrary.
enrich:
	uv run enrich.py

# Apply the home Ansible playbook (Proxmox host + LXCs).
# Pass LIMIT=apps (or another host pattern) to scope it.
home:
	ansible-playbook -i $(HOME_INVENTORY) infra/ansible/home.yml $(if $(LIMIT),--limit $(LIMIT),) $(if $(TAGS),--tags $(TAGS),)
