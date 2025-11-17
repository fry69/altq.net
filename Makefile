## Makefile for
## - preparing files to upload to the PDS server
## - uploading them
## - simple server management
##
## Requires ssh setup to loing as root into the PDS server
## and server name as set as SSH_HOSTNAME in .env file.
##
## Bugs:
## - hardcoded paths

ifeq ("$(wildcard .env)","")
$(error "No .env file found. Please copy .env.example to .env and fill it out.")
endif

include .env
## Exporting environment variables to sub-shells is not necessary
# export

all: copy-status copy-caddy install-timer

copy-status:
	scp bin/generate-status.py $(SSH_HOSTNAME):$(dir $(STATUS_SCRIPT_PATH))

copy-caddy: fmt
	scp caddy/etc/Caddyfile $(SSH_HOSTNAME):$(PDS_DIRECTORY)/caddy/etc/caddy
	scp caddy/webroot/* $(SSH_HOSTNAME):$(PDS_WEBROOT)

fmt:
	caddy fmt --overwrite --config caddy/etc/Caddyfile

install-timer:
	@echo "Installing timer service."
	@(cat .env | grep STATUS ; cat install-timer.sh) | ssh $(SSH_HOSTNAME) "bash -s"

generate: copy-status
	ssh $(SSH_HOSTNAME) "$(STATUS_SCRIPT_PATH) --pds-config $(PDS_DIRECTORY)/pds.env --output $(STATUS_OUTPUT_PATH)"

restart:
	ssh $(SSH_HOSTNAME) "systemctl restart pds"

status:
	ssh $(SSH_HOSTNAME) "systemctl status pds"

version:
	curl -s https://$(PDS_HOSTNAME)/xrpc/_health

