# Project Identity

**Type:** Infrastructure-as-Code (IaC) Deployment Template
**Description:** This repository is a deployment template for a remote server environment. It is NOT a standard software application with a build step.
**Context:** Many configuration files (e.g., `pds.env`, `*.j2`) are redacted or templated. These should be treated as placeholders or intended for runtime substitution, not as syntax errors or missing secrets.

## Stack Detection

**Container Services:**

- **Caddy** (v2) - Web Server & Reverse Proxy
- **PDS** (Bluesky Personal Data Server) - Core Service
- **Watchtower** - Container Auto-updater
- **Gatekeeper** - Access Control Sidecar

**Orchestration & Tools:**

- **Ansible Core** - Configuration Management
- **Docker Compose** (v3.9) - Container Orchestration
- **Systemd** - Service Management (Host level)
- **Python 3** - Status Generation Scripting
- **Bash** - Helper Scripts

## Safety Protocols

> [!IMPORTANT]
> **High Caution Execution Policy**
> Agents must **NEVER** auto-execute the following without explicit user confirmation:
> 
> - Ansible Playbooks (`ansible-playbook`, `*.yml`)
> - Shell Scripts (`*.sh`) that modify system state
> - Docker Compose commands that alter running containers
>
> **Always** ask for approval before running commands that modify the remote server state.

## File Classification

**Active (Orchestration & Scripts):**

- `site.yml` - Main Ansible Playbook for deployment.
- `Makefile` - Convenience wrapper for Ansible commands (primary interface).
- `install-timer.sh` - Script to install systemd timer for status reporting.
- `bin/generate-status.py` - Python script for generating status reports.

**Passive (Configuration & Definitions):**

- `compose.yaml` - Docker Compose service definitions.
- `caddy/etc/Caddyfile` - Caddy web server configuration.
- `ansible/group_vars/all.yml` - Global Ansible variables.
- `ansible/templates/*.j2` - Jinja2 templates for systemd units.
- `pds.env` / `pds.redacted.env` - Environment variable definitions.

## Operation Mapping

| User Intent | Mapped Command | Context |
| :--- | :--- | :--- |
| **Run / Deploy Project** | `make deploy` | Full deployment via Ansible (`ansible-playbook site.yml`). |
| **Dry Run / Preview Changes** | `make dry-run` | Shows what would change without applying (`--check --diff`). |
| **Update Caddy Config** | `make caddy` | Updates Caddy config & webroot only (`--tags caddy`). |
| **Update Status Script** | `make status-script` | Updates status script & systemd units (`--tags status`). |
| **Restart PDS Service** | `make restart` | Restarts the PDS systemd service (`--tags pds -e pds_restart=true`). |
| **Generate Status Page** | `make generate` | Manually triggers status page generation (`--tags status,run_once`). |
| **Check PDS Health** | `make version` | Checks PDS health endpoint (`--tags health`). |
| **Check Service Status** | `make status` | Checks PDS systemd service status (via `ansible pds -a`). |
