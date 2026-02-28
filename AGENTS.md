# AGENTS.md

## Cursor Cloud specific instructions

This is an **Odoo 17 custom module** (`odoo_mysql_connector`) that imports data from external MySQL databases into Odoo's PostgreSQL backend.

### Services

| Service | Purpose | How to start |
|---|---|---|
| PostgreSQL 16 | Odoo's internal database | `sudo service postgresql start` |
| MySQL 8.0 | External data source for the connector | `sudo service mysql start` |
| Odoo 17 dev server | Application runtime | See below |

### Running Odoo

Odoo 17 Community is installed at `/opt/odoo17`. The module is symlinked into `/opt/odoo17/custom-addons/odoo_mysql_connector`.

```
# Start Odoo in dev mode (hot-reload on Python changes)
export PATH="/home/ubuntu/.local/bin:$PATH"
python3 /opt/odoo17/odoo-bin -c /opt/odoo17/odoo-dev.conf -d odoo_dev --dev=all
```

Odoo listens on `http://localhost:8069`. Login: `admin` / `admin`.

### Gotchas

- **PostgreSQL auth**: `pg_hba.conf` is set to `md5` for local connections. The `odoo` PostgreSQL user has password `odoo` (configured in `/opt/odoo17/odoo-dev.conf`).
- **Module dependencies**: The manifest depends on `base`, `spreadsheet`, and `board` — all available in Odoo 17 Community (no Enterprise license needed).
- **MySQL test DB**: A test MySQL database `test_connector` exists with user `odoo_test` / `odoo_test_pass` and a sample `orders` table.
- **inotify warning**: Odoo may warn about missing `inotify` module; this is cosmetic and does not affect functionality. Install `inotify` pip package to suppress it.
- **Reinstalling the module**: Use `--update odoo_mysql_connector` flag (not `--init`) to update an already-installed module.

### Lint

```
export PATH="/home/ubuntu/.local/bin:$PATH"
flake8 --max-line-length=120 --ignore=E501,W503,W504 /workspace
```

Note: F401 "imported but unused" warnings in `__init__.py` files are expected Odoo convention.

### Tests

```
export PATH="/home/ubuntu/.local/bin:$PATH"
python3 /opt/odoo17/odoo-bin -c /opt/odoo17/odoo-dev.conf -d odoo_test --init odoo_mysql_connector --test-enable --test-tags odoo_mysql_connector --stop-after-init
```
