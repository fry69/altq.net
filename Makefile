## Makefile for PDS deployment via Ansible
##
## Requires:
## - Ansible installed
## - ansible/inventory.ini configured (or passed via ANSIBLE_ARGS)

ANSIBLE_CMD = ansible-playbook site.yml

.PHONY: all deploy caddy status-script restart generate status fmt

all: deploy

deploy:
	$(ANSIBLE_CMD)

dry-run:
	$(ANSIBLE_CMD) --check --diff

caddy:
	$(ANSIBLE_CMD) --tags caddy

status-script:
	$(ANSIBLE_CMD) --tags status

restart:
	$(ANSIBLE_CMD) --tags pds -e pds_restart=true

generate:
	$(ANSIBLE_CMD) --tags status,run_once -e status_run_once=true

status:
	ansible pds -a "systemctl status pds"

fmt:
	caddy fmt --overwrite --config caddy/etc/Caddyfile

version:
	$(ANSIBLE_CMD) --tags health
