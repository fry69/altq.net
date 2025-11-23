# PDS Modifications for <https://altq.net>

Please read the official PDS installation [README](https://github.com/bluesky-social/pds/blob/main/README.md) first.

## Main goals

- automate PDS configuration deployment
- allow serving a custom web page on PDS root
- generate a status page for PDS including account usage
  (see <https://altq.net/status.html>, hopefully boring enough)

## Features

- age restriction workaround, see [here](https://gist.github.com/mary-ext/6e27b24a83838202908808ad528b3318#method-5-self-hosted-pds)
- 2FA using [gatekeeper](https://tangled.org/baileytownsend.dev/pds-gatekeeper)
- CAR estimate

## Quick Start

### Prerequisites

- installed PDS server (see [README](https://github.com/bluesky-social/pds/blob/main/README.md))
- `ansible` 2.19+ installed locally (e.g. `brew install ansible`)
- SSH access to your PDS server as root

1. **Configure inventory**: Copy `ansible/inventory.sample.ini` to `ansible/inventory.ini` and set your server's hostname, SSH port, and any optional variables.

2. **Configure variables**: Edit `ansible/group_vars/all.yml` to set your `pds_hostname` and adjust any path defaults if needed.

3. **Deploy**:

   ```shell
   make dry-run       # Preview changes without applying
   make deploy        # Full deployment
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

## Notes

- The `generate-status.py` script requires Python's `psutil` library:

  ```shell
  apt install python3-psutil
  ```

- Caddy webroot configuration is already included in `compose.yaml`

## License

MIT, see [LICENSE](LICENSE).
