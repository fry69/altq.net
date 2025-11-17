## PDS Modifications for https://altq.net

Please read the official PDS installation [README](https://github.com/bluesky-social/pds/blob/main/README.md) first.

Goals:
- allow serving a custom web page on the PDS root
- generate a status page for the PDS including account usage

See https://altq.net/status.html how it looks (hopefully boring enough)

Detailed explanations: TBD

For now:
- my PDS runs on Ubuntu 24.04
- read and modify the files appropriately
- put them in their respective directories
- restart PDS via systemctl

There is a `Makefile` that might give you some hints.

To get Caddy to use your webroot and not its internal one, add this to `compose.yaml`:
```diff
--- orig/compose.yaml
+++ compose.yaml
@@ -14,6 +14,9 @@
       - type: bind
         source: /pds/caddy/etc/caddy
         target: /etc/caddy
+      - type: bind
+        source: /pds/caddy/webroot
+        target: /srv/webroot
   pds:
     container_name: pds
     image: ghcr.io/bluesky-social/pds:0.4
```

Note: The `generate-status.py` script needs the Python `psutil` library. Install it with e.g.
```shell
apt install python3-psutil
```

License: MIT