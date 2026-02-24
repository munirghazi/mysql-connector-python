# How to Check Sync Logs & Running Jobs

## 1. Check Running Sync (API Source Form)

1. Go to **MySDB Reporting → API Sources**
2. Open the API source record
3. Look at the **Last Sync** section:
   - **Sync In Progress**: `True` means a sync is currently running
   - **Last Sync Message**: Shows real-time progress, e.g. `Running… page 264 | created 2178 | updated 0`
   - **Sync Started At**: When the current sync began
4. **Refresh the page** (F5) periodically to see updated progress

---

## 2. Check from Odoo.sh Shell

Go to **Odoo.sh → Shell** tab and run:

### Currently running syncs
```python
env['mysdb.api.source'].search([('sync_in_progress', '=', True)]).mapped(lambda r: {
    'name': r.name,
    'started': str(r.sync_started_at),
    'page': r.last_sync_page,
    'message': r.last_sync_message,
})
```

### Last sync result for all sources
```python
env['mysdb.api.source'].search([]).mapped(lambda r: {
    'name': r.name,
    'status': r.last_sync_status,
    'count': r.last_sync_count,
    'page': r.last_sync_page,
    'message': r.last_sync_message,
    'at': str(r.last_sync_at),
})
```

### Recent sync log entries
```python
env['mysdb.sync.log'].search([], order='sync_datetime desc', limit=20).mapped(lambda r: {
    'source': r.source_name,
    'type': r.source_type,
    'status': r.sync_status,
    'message': r.sync_message,
    'at': str(r.sync_datetime),
})
```

---

## 3. Check from PostgreSQL (psql)

### Running syncs
```sql
SELECT name, sync_in_progress, sync_started_at, last_sync_page, last_sync_message
FROM mysdb_api_source
WHERE sync_in_progress = true;
```

### Last sync status for all sources
```sql
SELECT name, last_sync_status, last_sync_count, last_sync_page,
       last_sync_at, last_sync_message
FROM mysdb_api_source
ORDER BY last_sync_at DESC;
```

### Sync log history
```sql
SELECT source_type, source_name, sync_status, sync_message, sync_datetime
FROM mysdb_sync_log
ORDER BY sync_datetime DESC
LIMIT 20;
```

---

## 4. Check Odoo Logs (Odoo.sh)

1. Go to **Odoo.sh → Logs** tab
2. Filter/search for these log messages:

| Log Message | Meaning |
|---|---|
| `API Sync start` | A sync has started |
| `API Sync page done` | A page was processed (shows created/updated counts) |
| `API Sync finished` | Sync completed normally |
| `API Sync failed` | Sync encountered an error |
| `API rate limited (429)` | API rate limit hit, retrying |
| `Auto-sync completed` | Cron auto-sync finished |
| `Auto-sync failed` | Cron auto-sync encountered an error |
| `Skipping sync for` | Sync was skipped because another sync is running |
| `Clearing stale sync lock` | A stale lock (>2 hours) was auto-cleared |

---

## 5. Clear a Stuck Sync Lock

If a sync appears stuck (no progress for a long time):

### Option A: From the UI
1. Open the API source record
2. Click the **Clear Sync Lock** button (visible when sync is in progress)

### Option B: From Odoo.sh Shell
```python
src = env['mysdb.api.source'].search([('name', '=', 'YOUR_SOURCE_NAME')])
src.write({'sync_in_progress': False, 'sync_started_at': False})
env.cr.commit()
```

### Option C: From PostgreSQL
```sql
UPDATE mysdb_api_source
SET sync_in_progress = false, sync_started_at = NULL
WHERE name = 'YOUR_SOURCE_NAME';
```

> **Note**: Stale locks older than 2 hours are automatically cleared when the next sync attempt runs.
