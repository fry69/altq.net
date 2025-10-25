#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "psutil",
#   "jinija2",
#   "requests"
# ]
# ///


"""
Generate a simple, attractive HTML status page showing:
- System load, CPU %, root-disk usage, network usage
- PDS version retrieved from health endpoint
- Number of accounts and each account's DID
- Per-account store record/blob counts (from read-only SQLite)
- Estimated CAR export size for each repository
- Disk usage for each blocks directory by DID

Requires:
- Python 3.6+ (3.12+ recommended)
- psutil
- jinja2
- requests

Usage:
./generate_status.py --pds-config /pds/pds.env --output status.html
"""

import os
import argparse
import sqlite3
import psutil
import requests
from datetime import datetime, timedelta
from jinja2 import Environment


# Deterministic CAR layout constants derived from repo implementation
CAR_HEADER_TOTAL_BYTES = 59  # varint(58) + 58-byte dag-cbor header
CAR_BLOCK_CID_BYTES = 36  # CIDv1/sha256 byte length used in CAR streams


def parse_env_file(file_path):
    env_vars = {}

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            # Skip blank lines and comments
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value

    return env_vars


def human_readable_size(size, decimal_places=1):
    """Convert a size in bytes to a human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024.0 or unit == "PB":
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0
    return f"{size:.{decimal_places}f} PB"


def get_system_metrics(pds_path="/pds"):
    """Gather system load, CPU usage, /pds-disk stats, memory, kernel, and network usage."""
    load1, load5, load15 = os.getloadavg()
    cpu_percent = psutil.cpu_percent(interval=1)
    # Use /pds (or provided path) for disk usage
    usage = psutil.disk_usage("/")
    net = psutil.net_io_counters(pernic=True).get("eth0")
    net_sent = net.bytes_sent if net else 0
    net_recv = net.bytes_recv if net else 0
    uptime_seconds = int(psutil.boot_time())
    uptime = datetime.now() - datetime.fromtimestamp(uptime_seconds)
    # Memory info
    mem = psutil.virtual_memory()
    mem_total = mem.total
    mem_used = mem.total - mem.available
    mem_free = mem.available
    # Kernel version
    try:
        kernel_version = os.uname().release
    except AttributeError:
        import platform
        kernel_version = platform.uname().release

    return {
        "load1": load1,
        "load5": load5,
        "load15": load15,
        "cpu_percent": cpu_percent,
        "disk_total": usage.total,
        "disk_used": get_directory_usage(pds_path),
        "disk_free": usage.free,
        "disk_percent": usage.percent,
        "net_sent": net_sent,
        "net_recv": net_recv,
        "uptime": str(timedelta(seconds=int(uptime.total_seconds()))),
        "mem_total": mem_total,
        "mem_used": mem_used,
        "mem_free": mem_free,
        "kernel_version": kernel_version,
    }


def get_pds_version(host="localhost", port=3000):
    """Get the PDS version from the health endpoint."""
    try:
        response = requests.get(f"http://{host}:{port}/xrpc/_health", timeout=5)
        if response.status_code == 200:
            return response.json().get("version", "Unknown")
    except (requests.RequestException, ValueError):
        pass
    return "Unable to retrieve"


def get_account_data(pds_path):
    """Get total account count and list of DIDs from the account database."""
    account_db = os.path.join(pds_path, "account.sqlite")
    uri = f"file:{account_db}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM account")
    total_accounts = cur.fetchone()[0]

    cur.execute("SELECT did FROM account")
    dids = [row[0] for row in cur.fetchall()]

    conn.close()
    return total_accounts, dids


def find_store_db(pds_path, did):
    """Find the store.sqlite file for a given DID."""
    actors_root = os.path.join(pds_path, "actors")
    for root, dirs, files in os.walk(actors_root):
        if os.path.basename(root) == did and "store.sqlite" in files:
            return os.path.join(root, "store.sqlite")
    return None


def get_store_data(pds_path, did):
    """Get record/blob counts and repo CAR size estimate from a store database."""
    store_db = find_store_db(pds_path, did)
    if not store_db:
        raise FileNotFoundError(f"store.sqlite not found for DID {did}")

    uri = f"file:{store_db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM record")
    rec_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM blob")
    blob_count = cur.fetchone()[0]

    car_size_bytes = estimate_car_size_bytes(cur)

    conn.close()
    return rec_count, blob_count, car_size_bytes


def estimate_car_size_bytes(cur):
    """Reproduce repo->CAR sizing logic without reading blocks into memory."""
    # Sum block payloads, count rows, and get total varint overhead in a single query
    cur.execute(
        """
        SELECT
            COALESCE(SUM(size), 0) AS total_size,
            COUNT(*) AS block_count,
            COALESCE(SUM(
                CASE
                    WHEN size + ? < 128 THEN 1
                    WHEN size + ? < 16384 THEN 2
                    WHEN size + ? < 2097152 THEN 3
                    WHEN size + ? < 268435456 THEN 4
                    ELSE 5
                END
            ), 0) AS varint_bytes
        FROM repo_block
        """,
        (CAR_BLOCK_CID_BYTES,) * 4,
    )
    total_size, block_count, varint_bytes = cur.fetchone()
    total_size = total_size or 0
    block_count = block_count or 0
    varint_bytes = varint_bytes or 0

    # Total CAR = header + payload + CID bytes per block + length-prefix varints
    return (
        CAR_HEADER_TOTAL_BYTES
        + total_size
        + block_count * CAR_BLOCK_CID_BYTES
        + varint_bytes
    )


def get_directory_usage(path):
    """Calculate total disk usage of a directory."""
    total = 0
    for root, _, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def get_template():
    """Create and return a Jinja2 template for the status page."""
    template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Server Status</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-dark-5@1.1.3/dist/css/bootstrap-dark.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
        }
    </style>
</head>
<body class="bg-dark text-light">
    <div class="container">
        <h1 class="my-4">Server Status</h1>
        <p>Report generated: {{ generated }} (uptime: {{ metrics.uptime }}, kernel: {{ metrics.kernel_version }})</p>

        <h2>System Metrics</h2>
        <table class="table table-dark table-bordered">
            <tr>
                <th>Load (1m/5m/15m)</th>
                <th>CPU %</th>
                <th>Mem Used / Total</th>
                <th>Net Sent / Received</th>
                <th>Disk Used (/pds)</th>
                <th>Disk Free</th>
            </tr>
            <tr>
                <td>{{ "%.2f"|format(metrics.load1) }} / {{ "%.2f"|format(metrics.load5) }} / {{ "%.2f"|format(metrics.load15) }}</td>
                <td>{{ "%.1f"|format(metrics.cpu_percent) }}%</td>
                <td>{{ human_size(metrics.mem_used) }} / {{ human_size(metrics.mem_total) }}</td>
                <td>{{ human_size(metrics.net_sent) }} / {{ human_size(metrics.net_recv) }}</td>
                <td>{{ human_size(metrics.disk_used) }}</td>
                <td>{{ human_size(metrics.disk_free) }}</td>
            </tr>
        </table>

        <h2>Accounts in {{ pds_path }}</h2>
        <p>Total accounts: {{ total_accounts }} (PDS Version: {{ pds_version }})</p>
        <table class="table table-dark table-striped table-bordered">
            <thead>
                <tr>
                    <th>DID</th>
                    <th>Record Count</th>
                    <th>Blob Count</th>
                    <th>Blocks Dir Size</th>
                    <th>Repo CAR Size (est)</th>
                </tr>
            </thead>
            <tbody>
                {% for did, rec, blob, size, car_size in usage_list %}
                <tr>
                    <td>{{ did }}</td>
                    <td>{{ rec }}</td>
                    <td>{{ blob }}</td>
                    <td>{{ human_size(size) }}</td>
                    <td>
                        {% if car_size == "Error" %}
                            Error
                        {% else %}
                            {{ human_size(car_size) }}
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    # Create an environment with autoescape enabled
    env = Environment(autoescape=True)

    # Register the human_readable_size function as a filter for templates
    env.filters["human_size"] = human_readable_size

    # Create and return the template from the string
    return env.from_string(template_str)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a server status HTML report."
    )
    parser.add_argument(
        "--pds-config", help="Path to PDS configuration file (pds.env)", default=None
    )
    parser.add_argument("--output", default="status.html", help="Output HTML filename")
    parser.add_argument(
        "--pds-host", default="localhost", help="PDS host for version check"
    )
    parser.add_argument(
        "--pds-port", default=3000, type=int, help="PDS port for version check"
    )
    args = parser.parse_args()

    # Parse PDS configuration if provided
    if args.pds_config:
        _config = parse_env_file(args.pds_config)
        pds_data_directory = _config["PDS_DATA_DIRECTORY"]
        pds_blobstore_disk_location = _config["PDS_BLOBSTORE_DISK_LOCATION"]
    else:
        pds_data_directory = "/pds"
        pds_blobstore_disk_location = os.path.join(args.pds_path, "blocks")

    # Gather all data
    metrics = get_system_metrics(pds_data_directory)
    total_accounts, dids = get_account_data(pds_data_directory)
    usage_list = []

    for did in dids:
        try:
            rec_count, blob_count, car_size = get_store_data(pds_data_directory, did)
        except Exception:
            rec_count, blob_count, car_size = "Error", "Error", "Error"

        block_dir = os.path.join(pds_blobstore_disk_location, did)
        size = get_directory_usage(block_dir) if os.path.isdir(block_dir) else 0
        usage_list.append((did, rec_count, blob_count, size, car_size))

    # Sort usage_list by record count in descending order
    # Convert string 'Error' to -1 for sorting purposes
    usage_list.sort(key=lambda x: -1 if x[1] == "Error" else int(x[1]), reverse=True)

    # Get the template
    template = get_template()

    # Get timestamp with timezone
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    # If timezone is empty, assume UTC
    if timestamp.endswith(" "):
        timestamp = timestamp.strip() + " UTC"

    # Get PDS version
    pds_version = get_pds_version(args.pds_host, args.pds_port)

    # Render the template with our data
    rendered_html = template.render(
        metrics=metrics,
        generated=timestamp,
        total_accounts=total_accounts,
        usage_list=usage_list,
        pds_path=pds_data_directory,
        human_size=human_readable_size,
        pds_version=pds_version,
    )

    # Write output to file
    with open(args.output, "w") as f:
        f.write(rendered_html)

    print(f"Status page written to {args.output}")


if __name__ == "__main__":
    main()
