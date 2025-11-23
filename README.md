## PDS Modifications for <https://altq.net>

Please read the official PDS installation [README](https://github.com/bluesky-social/pds/blob/main/README.md) first.

Goals:

- allow serving a custom web page on the PDS root
- generate a status page for the PDS including account usage

See <https://altq.net/status.html> how it looks (hopefully boring enough)

Detailed explanations: TBD

For now:

- my PDS runs on Ubuntu 24.04
- read and modify the files appropriately
- put them in their respective directories
- restart PDS via systemctl

## Quick Start

Prereqs:

- `ansible-core` 2.20+ installed locally
- SSH access to your PDS server as root

1. **Configure inventory**: Copy `ansible/inventory.sample.ini` to `ansible/inventory.ini` and set your server's hostname, SSH port, and any optional variables.

2. **Configure variables**: Edit `ansible/group_vars/all.yml` to set your `pds_hostname` and adjust any path defaults if needed.

3. **Deploy**:

   ```shell
   make deploy        # Full deployment
   make dry-run       # Preview changes without applying
   ```

### Available Commands

| Command | Description |
|---------|-------------|
| `make deploy` | Deploy all changes to the server |
| `make dry-run` | Preview what would change (doesn't modify server) |
| `make caddy` | Update only Caddy configuration |
| `make status-script` | Update only the status script |
| `make restart` | Restart the PDS service |
| `make generate` | Manually trigger status page generation |
| `make version` | Check PDS health |
| `make status` | Check PDS service status |

### Notes

- The `generate-status.py` script requires Python's `psutil` library:

  ```shell
  apt install python3-psutil
  ```

- Caddy webroot configuration is already included in `compose.yaml`

License: MIT
