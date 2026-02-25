# -*- coding: utf-8 -*-
import json
import threading
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
import os
import re
from datetime import datetime, timedelta

import odoo
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, config
from odoo.exceptions import ValidationError
from .mysdb_date_utils import normalize_datetime as _normalize_dt, normalize_date as _normalize_d

_logger = logging.getLogger(__name__)


class MysdbApiSource(models.Model):
    _name = 'mysdb.api.source'
    _description = 'MySDB API Source'
    _rec_name = 'name'

    name = fields.Char(string='Association Name', required=True)
    api_url = fields.Char(string='API Base URL')
    request_url = fields.Char(
        string='Request URL',
        required=True,
        help="Full URL or relative path. Supports {page} and {page_size} placeholders."
    )
    bearer_token = fields.Text(string='Bearer Token')
    custom_headers = fields.Text(
        string='Custom Headers (JSON)',
        help=(
            "Optional JSON object of extra HTTP headers sent with every request.\n"
            "Example: {\"X-Manager-Token\": \"abc123\", \"Accept-Language\": \"ar\"}\n"
            "These are merged with (and override) the default Authorization header."
        ),
    )
    target_model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        required=False,
        domain="[('model', '=ilike', 'mysdb.%')]",
        ondelete='set null'
    )
    unique_field = fields.Char(
        string='Unique Field',
        help="Field used to upsert (e.g. order_id, product_id). Leave empty to always create."
    )
    data_root_key = fields.Char(
        string='Data Root Key',
        help=(
            "JSON key that contains the list of items.\n"
            "Leave empty to auto-detect (tries 'data', 'items', 'result', 'results').\n"
            "Examples: 'orders' for Zid, 'data' for Jood/Bayan."
        )
    )
    mapping_json = fields.Json(
        string='Field Mapping',
        help=(
            "JSON mapping of target_field -> source_key. "
            "Supports dot-notation for nested fields: "
            "{'customer_name': 'customer.name', 'payment_method_name': 'payment.method.name'}. "
            "Constants: {'store_id': {'const': '123'}} or {'store_id': 'const:123'}."
        )
    )
    enable_pagination = fields.Boolean(string='Enable Pagination', default=False)
    pagination_start = fields.Integer(string='Start Page', default=1)
    pagination_zero_based = fields.Boolean(string='Zero-based Page Index', default=False)
    page_size = fields.Integer(string='Page Size', default=50)
    page_request_delay = fields.Float(
        string='Page Request Delay (sec)', default=0,
        help="Seconds to wait between page requests (rate limiting). "
             "Set to 1-2 for APIs with rate limits like Zid."
    )
    connect_timeout = fields.Integer(string='Connect Timeout (sec)', default=20)
    request_timeout = fields.Integer(string='Request Timeout (sec)', default=60)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        help='Company that owns this API source. Leave empty for shared access.'
    )
    auto_sync = fields.Boolean(
        string='Auto Sync', default=False,
        help='If enabled, this API source will be synced automatically by the system scheduler.'
    )

    @api.constrains('auto_sync', 'unique_field')
    def _check_auto_sync_unique_field(self):
        for rec in self:
            if rec.auto_sync and not rec.unique_field:
                raise ValidationError(
                    _("Cannot enable Auto Sync without a Unique Field. "
                      "Without a unique field, every sync run would create "
                      "duplicate records. Please set the Unique Field first.")
                )
    auto_sync_interval = fields.Integer(
        string='Sync Every', default=1,
        help='How often to auto-sync this source.',
    )
    auto_sync_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
    ], string='Interval Type', default='hours')
    auto_sync_next_run = fields.Datetime(
        string='Next Scheduled Run', readonly=True,
        help='When this source will be synced next. Automatically calculated after each sync.',
    )
    sync_in_progress = fields.Boolean(
        string='Sync In Progress', default=False, readonly=True,
        help='Indicates a sync is currently running. Prevents concurrent syncs.'
    )
    sync_started_at = fields.Datetime(
        string='Sync Started At', readonly=True,
        help='When the current sync started. Used for stale-lock detection.'
    )

    filter_date_from = fields.Datetime(string='Filter Date From')
    filter_date_to = fields.Datetime(string='Filter Date To')
    filter_date_from_param = fields.Char(string='From Param', default='fromDate')
    filter_date_to_param = fields.Char(string='To Param', default='toDate')
    filter_date_format = fields.Char(string='Date Format', default='%Y-%m-%d')
    filter_status_name_enabled = fields.Boolean(string='Filter by Status Name', default=False)
    filter_status_name = fields.Char(string='Status Name', default='عملية مقبولة')

    dump_json = fields.Boolean(string='Dump Raw JSON', default=False)
    dump_directory = fields.Char(string='Dump Directory')
    dump_file_prefix = fields.Char(string='Dump File Prefix', default='api_dump')
    last_dump_file = fields.Char(string='Last Dump File', readonly=True)
    last_dump_size = fields.Integer(string='Last Dump Size (bytes)', readonly=True)

    last_sync_at = fields.Datetime(string='Last Sync At', readonly=True)
    last_sync_status = fields.Selection(
        [('ok', 'OK'), ('error', 'Error')],
        string='Last Sync Status',
        readonly=True
    )
    last_sync_message = fields.Text(string='Last Sync Message', readonly=True)
    last_sync_count = fields.Integer(string='Last Sync Count', readonly=True)
    last_sync_page = fields.Integer(string='Last Sync Page', readonly=True)
    last_sync_page_items = fields.Integer(string='Last Page Items', readonly=True)
    last_sync_page_created = fields.Integer(string='Last Page Created', readonly=True)
    last_sync_page_updated = fields.Integer(string='Last Page Updated', readonly=True)

    # ------------------------------------------------------------------
    #  Detail Sync – per-record child fetching (e.g. Zid order products)
    #  This does NOT affect Jood/Bayan which use _sync_project_list().
    # ------------------------------------------------------------------
    detail_sync_enabled = fields.Boolean(
        'Enable Detail Sync', default=False,
        help="When enabled, a second pass fetches child records for each "
             "parent record via a per-record API call (e.g. order products)."
    )
    detail_url_pattern = fields.Char(
        'Detail URL Pattern',
        help="URL template with {id} placeholder.\n"
             "Example: https://api.zid.sa/v1/managers/store/orders/{id}/view"
    )
    detail_parent_id_field = fields.Char(
        'Parent ID Field', default='order_id',
        help="Field on the parent model whose value replaces {id} in the URL."
    )
    detail_parent_domain = fields.Text(
        'Parent Filter Domain',
        help='Optional JSON domain to scope which parent records to process.\n'
             'Example: [["store_id","=","1170879"]]'
    )
    detail_data_root_key = fields.Char(
        'Detail Data Root Key',
        help="Dot-notation path to the child items list.\n"
             "Example: order.products"
    )
    detail_target_model_id = fields.Many2one(
        'ir.model', string='Detail Target Model',
        domain="[('model', '=ilike', 'mysdb.%')]",
        ondelete='set null',
    )
    detail_unique_field = fields.Char(
        'Detail Unique Field',
        help="Field used to upsert detail records (e.g. order_detail_uuid)."
    )
    detail_mapping_json = fields.Text(
        'Detail Field Mapping',
        help=(
            "JSON mapping for detail records.\n"
            "Use 'parent:key' to pull values from the parent object "
            "(the container of the items list).\n"
            "Example:\n"
            '{"order_linked_id":"parent:id","store_id":"parent:store_id",'
            '"product_name":"name","product_sku":"sku","total":"total"}'
        )
    )
    detail_request_delay = fields.Float(
        'Detail Request Delay (sec)', default=0.3,
        help="Seconds to wait between per-record API calls."
    )
    detail_last_sync_at = fields.Datetime('Detail Last Sync At', readonly=True)
    detail_last_sync_status = fields.Selection(
        [('ok', 'OK'), ('error', 'Error')],
        string='Detail Sync Status', readonly=True,
    )
    detail_last_sync_message = fields.Text('Detail Sync Message', readonly=True)
    detail_last_sync_count = fields.Integer('Detail Sync Count', readonly=True)

    def _build_request_url(self, page=None):
        url = (self.request_url or '').strip()
        if not url:
            raise ValidationError(_("Request URL is required."))
        page_val = page if page is not None else self.pagination_start
        if page_val is None:
            page_val = 0
        if self.pagination_zero_based:
            page_val = int(page_val)
        else:
            page_val = int(page_val)
        if '{page}' in url or '{page_size}' in url:
            url = url.format(page=page_val, page_size=self.page_size)
        if not url.lower().startswith(('http://', 'https://')):
            base = (self.api_url or '').rstrip('/') + '/'
            url = urllib.parse.urljoin(base, url.lstrip('/'))
        if self.enable_pagination and '{page}' not in (self.request_url or ''):
            parsed = urllib.parse.urlparse(url)
            query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
            current_page = str(page_val)
            current_size = str(self.page_size)
            # Common pagination params — try to reuse whatever key is
            # already in the URL; fall back to 'pageNumber' (Jood-style).
            if 'pageIndex' in query:
                query['pageIndex'] = current_page
            elif 'pageNumber' in query:
                query['pageNumber'] = current_page
            elif 'page' in query:
                query['page'] = current_page
            elif 'pageNo' in query:
                query['pageNo'] = current_page
            else:
                query['pageNumber'] = current_page
            if 'pageSize' in query:
                query['pageSize'] = current_size
            elif 'page_size' in query:
                query['page_size'] = current_size
            elif 'limit' in query:
                query['limit'] = current_size
            else:
                query['pageSize'] = current_size
            url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
        if self.filter_date_from or self.filter_date_to:
            url = self._apply_date_filters(url)
        return url

    def _apply_date_filters(self, url):
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        date_format = self.filter_date_format or '%Y-%m-%d'
        if self.filter_date_from and self.filter_date_from_param:
            query[self.filter_date_from_param] = self.filter_date_from.strftime(date_format)
        if self.filter_date_to and self.filter_date_to_param:
            query[self.filter_date_to_param] = self.filter_date_to.strftime(date_format)
        return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))

    def _fetch_json(self, url):
        headers = {
            'Accept': 'application/json',
        }
        if self.bearer_token:
            headers['Authorization'] = f"Bearer {self.bearer_token.strip()}"
        # Merge custom headers (can override defaults if needed)
        if self.custom_headers:
            try:
                extra = json.loads(self.custom_headers)
                if isinstance(extra, dict):
                    headers.update(extra)
            except (json.JSONDecodeError, TypeError) as e:
                _logger.warning("Invalid custom_headers JSON: %s", e)
        _logger.info(
            "API fetch: url=%s headers=%s",
            url,
            {k: (v[:30] + '…' if len(str(v)) > 30 else v) for k, v in headers.items()},
        )
        req = urllib.request.Request(url, headers=headers)
        timeout = self.request_timeout or self.connect_timeout or 20
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    status = resp.status
                    content_type = resp.headers.get('Content-Type', '')
                break  # success
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < max_retries:
                    # Rate limited – back off and retry
                    retry_after = int(exc.headers.get('Retry-After', 0)) or (5 * (attempt + 1))
                    _logger.warning(
                        "API rate limited (429): source=%s url=%s retry_after=%ss attempt=%s/%s",
                        self.name, url, retry_after, attempt + 1, max_retries,
                    )
                    time.sleep(retry_after)
                    continue
                try:
                    error_body = exc.read().decode('utf-8', errors='ignore')[:2000]
                except Exception:
                    error_body = ''
                # Treat 404 "Invalid page" as end-of-pagination (empty result)
                if exc.code == 404 and 'invalid page' in error_body.lower():
                    _logger.info(
                        "API pagination end (404 Invalid page): url=%s", url,
                    )
                    return {}, b'{}'
                raise ValidationError(
                    _("HTTP Error %s: %s\nURL: %s\nResponse: %s") % (
                        exc.code, exc.reason, url, error_body
                    )
                )
            except urllib.error.URLError as exc:
                raise ValidationError(
                    _("Connection error: %s\nURL: %s") % (str(exc.reason), url)
                )
        _logger.info(
            "API response: status=%s content_type=%s size=%s bytes",
            status, content_type, len(raw),
        )
        if not raw:
            raise ValidationError(
                _("Empty response from API.\nURL: %s\nHTTP Status: %s\n"
                  "Content-Type: %s\nCheck your authentication headers and URL.")
                % (url, status, content_type)
            )
        try:
            return json.loads(raw.decode('utf-8')), raw
        except Exception as exc:
            # Show first 500 chars of response for debugging
            preview = raw.decode('utf-8', errors='ignore')[:500]
            raise ValidationError(
                _("Invalid JSON response: %s\nURL: %s\nResponse preview:\n%s")
                % (str(exc), url, preview)
            )

    def _resolve_dotted_key(self, item, dotted_key):
        """Resolve a dot-notation key path like 'customer.name' or
        'payment.method.code' against a nested dict."""
        parts = str(dotted_key).split('.')
        current = item
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _extract_items(self, payload):
        items = []
        if isinstance(payload, list):
            items = payload
        if isinstance(payload, dict):
            # If a custom root key is configured, try it first
            root_key = (self.data_root_key or '').strip()
            if root_key:
                val = payload.get(root_key)
                if isinstance(val, list):
                    items = val
                elif val is not None:
                    _logger.warning(
                        "API data_root_key '%s' did not contain a list (got %s). "
                        "Falling back to auto-detect.",
                        root_key, type(val).__name__,
                    )
            if not items:
                for key in ('data', 'items', 'result', 'results', 'orders', 'products'):
                    val = payload.get(key)
                    if isinstance(val, list):
                        items = val
                        break
        if self.filter_status_name_enabled and self.filter_status_name:
            items = [
                item for item in items
                if isinstance(item, dict) and item.get('statusName') == self.filter_status_name
            ]
        return items

    @staticmethod
    def _extract_pagination_meta(payload):
        """Extract total-page / total-record counts from API response metadata.

        Common API patterns looked for (in order):
          • top-level: last_page, lastPage, total_pages, totalPages, pageCount
          • nested:    pagination.last_page, pagination.totalPages, meta.last_page
          • counts:    total, count, totalCount  (used to estimate total pages)
        Returns (total_pages, total_records) — either may be None.
        """
        if not isinstance(payload, dict):
            return None, None

        total_pages = None
        total_records = None

        # --- Direct page-count keys ---
        for key in ('last_page', 'lastPage', 'total_pages', 'totalPages',
                     'pageCount', 'page_count', 'pages', 'numberOfPages'):
            val = payload.get(key)
            if val is not None:
                try:
                    total_pages = int(val)
                    break
                except (ValueError, TypeError):
                    pass

        # --- Nested in 'pagination' or 'meta' ---
        if total_pages is None:
            for wrapper_key in ('pagination', 'meta', 'paging', 'paginator'):
                wrapper = payload.get(wrapper_key)
                if isinstance(wrapper, dict):
                    for key in ('last_page', 'lastPage', 'total_pages',
                                'totalPages', 'pageCount', 'page_count'):
                        val = wrapper.get(key)
                        if val is not None:
                            try:
                                total_pages = int(val)
                                break
                            except (ValueError, TypeError):
                                pass
                if total_pages is not None:
                    break

        # --- Total record count ---
        for key in ('total', 'count', 'totalCount', 'total_count',
                     'totalRecords', 'total_records'):
            val = payload.get(key)
            if val is not None:
                try:
                    total_records = int(val)
                    break
                except (ValueError, TypeError):
                    pass
        if total_records is None:
            for wrapper_key in ('pagination', 'meta', 'paging', 'paginator'):
                wrapper = payload.get(wrapper_key)
                if isinstance(wrapper, dict):
                    for key in ('total', 'count', 'totalCount', 'total_count'):
                        val = wrapper.get(key)
                        if val is not None:
                            try:
                                total_records = int(val)
                                break
                            except (ValueError, TypeError):
                                pass
                if total_records is not None:
                    break

        return total_pages, total_records

    @staticmethod
    def _format_eta(seconds):
        """Format seconds into a human-readable duration string."""
        if seconds is None or seconds < 0:
            return "unknown"
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        secs = seconds % 60
        if minutes < 60:
            return f"{minutes}m {secs:02d}s"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins:02d}m"

    def _map_item_to_values(self, item, model_fields):
        values = {}
        mapping = self.mapping_json or {}
        if isinstance(mapping, str):
            try:
                mapping = json.loads(mapping)
            except Exception as exc:
                raise ValidationError(_("Field Mapping must be valid JSON. %s") % str(exc))
        if mapping:
            for target_field, source_key in mapping.items():
                if target_field not in model_fields:
                    continue
                raw_val = None
                if isinstance(source_key, dict) and 'const' in source_key:
                    raw_val = source_key.get('const')
                elif isinstance(source_key, str) and source_key.startswith('const:'):
                    raw_val = source_key.split('const:', 1)[1]
                elif isinstance(source_key, str) and '.' in source_key:
                    # Dot-notation for nested fields: "customer.name"
                    raw_val = self._resolve_dotted_key(item, source_key)
                elif source_key in item:
                    raw_val = item.get(source_key)
                if raw_val is not None:
                    values[target_field] = self._coerce_value(target_field, raw_val, model_fields)
        else:
            for key, val in item.items():
                if key in model_fields:
                    values[key] = self._coerce_value(key, val, model_fields)
                else:
                    normalized_key = self._normalize_source_key(key)
                    if normalized_key in model_fields:
                        values[normalized_key] = self._coerce_value(normalized_key, val, model_fields)
        if (
            self.target_model_id
            and self.target_model_id.model == 'mysdb.order'
            and 'order_created_at' in model_fields
            and 'order_created_at' not in values
        ):
            for key in (
                'orderCreatedAt',
                'order_created_at',
                'createdAt',
                'created_at',
                'orderDate',
                'order_date',
                'date',
            ):
                if key in item and item.get(key):
                    values['order_created_at'] = self._coerce_value(
                        'order_created_at',
                        item.get(key),
                        model_fields
                    )
                    break
        return values

    def _normalize_source_key(self, key):
        if not key:
            return ''
        key = str(key).strip()
        key = re.sub(r'[\s\-]+', '_', key)
        key = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', key)
        key = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', key)
        key = re.sub(r'_+', '_', key)
        return key.lower().strip('_')

    def _coerce_value(self, field_name, value, model_fields):
        field = model_fields.get(field_name)
        if not field:
            return value
        if field.type == 'datetime' and isinstance(value, str):
            return self._normalize_datetime(value)
        if field.type == 'date' and isinstance(value, str):
            return self._normalize_date(value)
        if field.type == 'float' and isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        if field.type == 'integer' and isinstance(value, str):
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return value
        if field.type == 'char' and not isinstance(value, str):
            return str(value)
        if field.type == 'boolean' and not isinstance(value, bool):
            return bool(value)
        return value

    def _normalize_datetime(self, value):
        """Delegate to shared date utility."""
        return _normalize_dt(value)

    def _normalize_date(self, value):
        """Delegate to shared date utility."""
        return _normalize_d(value)

    def _upsert_items(self, items):
        model_name = self.target_model_id.model
        model = self.env[model_name].sudo()
        model_fields = model._fields
        detail_model = self.env['mysdb.order.detail'].sudo()
        is_order = model_name == 'mysdb.order'

        created = 0
        updated = 0
        errors = 0

        # Parse unique fields once
        unique_fields = []
        if self.unique_field:
            unique_fields = [
                f.strip()
                for f in str(self.unique_field).replace(';', ',').split(',')
                if f.strip() and f.strip() in model_fields
            ]

        # ---------- Prepare all mapped values ----------
        mapped_items = []  # list of (values_dict, original_item)
        for item in items:
            if not isinstance(item, dict):
                continue
            values = self._map_item_to_values(item, model_fields)
            if values:
                mapped_items.append((values, item))

        if not mapped_items:
            return 0, 0

        # ---------- Batch lookup existing records ----------
        existing_map = {}  # key_tuple -> recordset
        if unique_fields:
            # Build a mapping of key_tuple -> values for batch lookup
            keys_to_lookup = []
            for values, _item in mapped_items:
                key_vals = tuple(values.get(f) for f in unique_fields)
                if any(v in (None, False, '') for v in key_vals):
                    continue
                keys_to_lookup.append(key_vals)

            if keys_to_lookup and len(unique_fields) == 1:
                # Single unique field – use a single 'in' query
                field_name = unique_fields[0]
                all_vals = list(set(k[0] for k in keys_to_lookup))
                # Search in batches of 1000 to avoid huge IN clauses
                for i in range(0, len(all_vals), 1000):
                    batch_vals = all_vals[i:i+1000]
                    recs = model.search([(field_name, 'in', batch_vals)])
                    for rec in recs:
                        key = (getattr(rec, field_name),)
                        existing_map[key] = rec
            elif keys_to_lookup and len(unique_fields) > 1:
                # Multiple unique fields – batch lookup using OR domain
                # Group into batches of 200 to keep query size reasonable
                unique_key_set = list(set(keys_to_lookup))
                for i in range(0, len(unique_key_set), 200):
                    batch_keys = unique_key_set[i:i+200]
                    or_domain = []
                    for key_vals in batch_keys:
                        sub_domain = [(f, '=', v) for f, v in zip(unique_fields, key_vals)]
                        if or_domain:
                            or_domain = ['|'] + sub_domain + or_domain
                        else:
                            or_domain = sub_domain
                    recs = model.search(or_domain)
                    for rec in recs:
                        key = tuple(getattr(rec, f) for f in unique_fields)
                        existing_map[key] = rec

        _logger.info(
            "API upsert batch: source=%s total_items=%s existing_found=%s",
            self.name, len(mapped_items), len(existing_map),
        )

        # ---------- Split into creates vs updates ----------
        # Also dedup within the page: if the same key appears multiple times,
        # keep only the LAST occurrence (latest data wins).
        to_update = []       # list of (record, values, item)
        no_key_create = []   # items with no/missing unique key
        create_dedup = {}    # key_tuple -> (values, item)  — last-one-wins

        for values, item in mapped_items:
            if unique_fields:
                key_vals = tuple(values.get(f) for f in unique_fields)
                if any(v in (None, False, '') for v in key_vals):
                    no_key_create.append((values, item))
                    continue
                existing_rec = existing_map.get(key_vals)
                if existing_rec:
                    to_update.append((existing_rec, values, item))
                else:
                    # Dedup within same page – last occurrence wins
                    create_dedup[key_vals] = (values, item)
            else:
                no_key_create.append((values, item))

        to_create = list(create_dedup.values())
        dedup_saved = len(mapped_items) - len(to_update) - len(to_create) - len(no_key_create)
        if dedup_saved > 0:
            _logger.info(
                "API upsert dedup: source=%s removed %s within-page duplicates",
                self.name, dedup_saved,
            )

        # ---------- Batch UPDATE ----------
        for rec, values, item in to_update:
            try:
                with self.env.cr.savepoint():
                    rec.write(values)
                    updated += 1
                    if is_order:
                        self._sync_project_list(item, detail_model)
            except Exception as e:
                errors += 1
                _logger.warning(
                    "API upsert update failed: source=%s key=%s error=%s",
                    self.name,
                    {f: values.get(f) for f in unique_fields},
                    str(e)[:200],
                )

        # ---------- Batch CREATE ----------
        all_to_create = to_create + no_key_create
        if all_to_create:
            BATCH_SIZE = 500
            for i in range(0, len(all_to_create), BATCH_SIZE):
                batch = all_to_create[i:i+BATCH_SIZE]
                batch_vals = [v for v, _item in batch]
                try:
                    with self.env.cr.savepoint():
                        model.create(batch_vals)
                        created += len(batch)
                        if is_order:
                            for _v, item in batch:
                                self._sync_project_list(item, detail_model)
                except Exception as batch_err:
                    _logger.warning(
                        "API batch create failed (%s records), falling back to one-by-one: %s",
                        len(batch), str(batch_err)[:200],
                    )
                    # Fall back to one-by-one
                    for values, item in batch:
                        try:
                            with self.env.cr.savepoint():
                                model.create([values])
                                created += 1
                                if is_order:
                                    self._sync_project_list(item, detail_model)
                        except Exception as e:
                            errors += 1
                            _logger.warning(
                                "API single create failed: source=%s error=%s",
                                self.name, str(e)[:200],
                            )

        if errors:
            _logger.warning(
                "API upsert completed with errors: source=%s created=%s updated=%s errors=%s",
                self.name, created, updated, errors,
            )
        return created, updated

    def _sync_project_list(self, item, detail_model):
        project_list = item.get('projectList') or []
        if not isinstance(project_list, list) or not project_list:
            return
        order_id = item.get('id')
        if order_id is None:
            return
        order_linked_id = str(order_id)
        detail_store_id = (
            item.get('storeId')
            or item.get('store_id')
            or item.get('storeCode')
        )
        detail_created_at = (
            item.get('orderCreatedAt')
            or item.get('createdAt')
            or item.get('created_at')
            or item.get('creationDate')
            or item.get('donationDate')
            or item.get('orderDate')
            or item.get('date')
        )
        if isinstance(detail_created_at, str):
            detail_created_at = self._normalize_datetime(detail_created_at)
        if not detail_created_at or not detail_store_id:
            try:
                order_rec = self.env['mysdb.order'].sudo().search(
                    [('order_id', '=', order_linked_id)],
                    limit=1
                )
                if order_rec:
                    if not detail_created_at:
                        detail_created_at = order_rec.order_created_at
                    if not detail_store_id:
                        detail_store_id = order_rec.store_id
            except Exception:
                pass

        for project in project_list:
            if not isinstance(project, dict):
                continue
            product_name = project.get('projectName') or ''
            product_sku = project.get('categoryName') or ''
            unit_price = project.get('amount')
            if unit_price is None:
                unit_price = 0.0
            quantity = project.get('quantity')
            if quantity is None:
                quantity = 0.0
            try:
                total = float(unit_price) * float(quantity)
            except (ValueError, TypeError):
                total = 0.0

            if not product_name and not product_sku and total == 0.0:
                continue

            try:
                with self.env.cr.savepoint():
                    # Prefer a stable match (order + product identifiers). Fall back to amount/qty.
                    base_domain = [
                        ('order_linked_id', '=', order_linked_id),
                        ('product_name', '=', product_name),
                        ('product_sku', '=', product_sku),
                    ]
                    existing = detail_model.search(base_domain, limit=1)
                    if not existing:
                        fallback_domain = [
                            ('order_linked_id', '=', order_linked_id),
                            ('product_name', '=', product_name),
                            ('total', '=', total),
                            ('quantity', '=', quantity),
                        ]
                        existing = detail_model.search(fallback_domain, limit=1)
                    vals = {
                        'order_linked_id': order_linked_id,
                        'product_name': product_name,
                        'product_sku': product_sku,
                        'total': total,
                        'quantity': quantity,
                        'created_at': detail_created_at,
                        'store_id': detail_store_id,
                    }
                    if existing:
                        existing.write(vals)
                    else:
                        detail_model.create(vals)
            except Exception as e:
                _logger.warning(
                    "sync_project_list: failed for order %s project %s: %s",
                    order_linked_id, product_name[:50], str(e)[:200],
                )

    # ==================================================================
    #  DETAIL SYNC – per-record child fetching (e.g. Zid order → products)
    #  Completely independent of _sync_project_list (Jood/Bayan).
    # ==================================================================

    def action_sync_details(self):
        """Start detail sync in a background thread and return immediately."""
        for rec in self:
            if not rec.detail_sync_enabled:
                raise ValidationError(
                    _("Detail Sync is not enabled for '%s'.") % rec.name
                )
            rec.write({
                'detail_last_sync_at': fields.Datetime.now(),
                'detail_last_sync_status': 'ok',
                'detail_last_sync_message': 'Detail sync started – running in background…',
                'detail_last_sync_count': 0,
            })
        self.env.cr.commit()

        dbname = self.env.cr.dbname
        uid = self.env.uid
        rec_ids = self.ids

        t = threading.Thread(
            target=self._detail_sync_in_background,
            args=(dbname, uid, rec_ids),
            daemon=True,
        )
        t.start()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Detail Sync Started'),
                'message': _(
                    'Detail sync is running in the background. '
                    'Refresh the page to see progress.'
                ),
                'type': 'info',
                'sticky': False,
            },
        }

    @classmethod
    def _detail_sync_in_background(cls, dbname, uid, rec_ids):
        """Execute detail sync in a new cursor / environment."""
        try:
            registry = odoo.registry(dbname)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, uid, {})
                sources = env['mysdb.api.source'].browse(rec_ids).exists()
                for rec in sources:
                    try:
                        rec._do_sync_details()
                    except Exception as e:
                        _logger.exception(
                            "Detail sync crashed for source %s: %s",
                            rec.name, str(e)[:500],
                        )
                        try:
                            cr.rollback()
                            rec.write({
                                'detail_last_sync_at': fields.Datetime.now(),
                                'detail_last_sync_status': 'error',
                                'detail_last_sync_message': (
                                    "Background thread error: %s" % str(e)[:500]
                                ),
                            })
                            cr.commit()
                        except Exception:
                            _logger.exception(
                                "Failed to write error status for detail sync %s",
                                rec.name,
                            )
        except Exception:
            _logger.exception(
                "Background detail sync thread crashed (ids=%s)", rec_ids
            )

    def _do_sync_details(self):
        """Fetch child records for each parent record via per-record API."""
        rec = self
        total_created = 0
        total_updated = 0
        total_skipped = 0
        total_errors = 0
        total_fetched = 0

        try:
            if not rec.detail_url_pattern or not rec.detail_target_model_id:
                raise ValidationError(
                    _("Detail URL Pattern and Detail Target Model are required.")
                )

            parent_model = self.env[rec.target_model_id.model].sudo()
            detail_model = self.env[rec.detail_target_model_id.model].sudo()
            detail_fields = detail_model._fields
            id_field = (rec.detail_parent_id_field or 'order_id').strip()

            # Parse detail mapping
            mapping = {}
            if rec.detail_mapping_json:
                raw = rec.detail_mapping_json
                if isinstance(raw, str):
                    mapping = json.loads(raw)
                elif isinstance(raw, dict):
                    mapping = raw
            if not mapping:
                raise ValidationError(_("Detail Field Mapping is required."))

            # Parse optional parent domain filter
            parent_domain = []
            if rec.detail_parent_domain:
                try:
                    parent_domain = json.loads(rec.detail_parent_domain)
                except Exception:
                    _logger.warning(
                        "Invalid detail_parent_domain JSON, ignoring: %s",
                        rec.detail_parent_domain,
                    )

            # ------ Determine which parents already have details ------
            # Find the mapping entry that links child → parent ID
            detail_link_field = None
            for tf, sk in mapping.items():
                if isinstance(sk, str) and sk.startswith('parent:'):
                    parent_key = sk.split('parent:', 1)[1]
                    if parent_key in ('id', 'order_id'):
                        detail_link_field = tf
                        break

            # Fetch all parent records
            parents = parent_model.search(parent_domain, order='id asc')
            parent_list = []
            missing_id_count = 0
            for p in parents:
                pid = getattr(p, id_field, None)
                if pid:
                    parent_list.append((str(pid), p))
                else:
                    missing_id_count += 1

            _logger.info(
                "Detail sync start: source=%s parents=%s (missing_id=%s) "
                "detail_model=%s id_field=%s domain=%s",
                rec.name, len(parent_list), missing_id_count,
                rec.detail_target_model_id.model, id_field,
                parent_domain or '[]',
            )

            # --- Diagnostic: if 0 parents found, explain why ---
            if not parent_list:
                total_in_model = parent_model.search_count([])
                diag_parts = []
                if total_in_model == 0:
                    diag_parts.append(
                        "Target model %s has 0 records. "
                        "Run the main sync first to populate orders."
                        % rec.target_model_id.model
                    )
                else:
                    diag_parts.append(
                        "Target model %s has %s total records"
                        % (rec.target_model_id.model, total_in_model)
                    )
                    if parent_domain:
                        matched = parent_model.search_count(parent_domain)
                        diag_parts.append(
                            "but domain %s matches only %s"
                            % (parent_domain, matched)
                        )
                    if missing_id_count > 0:
                        diag_parts.append(
                            "%s records have empty '%s' field"
                            % (missing_id_count, id_field)
                        )
                    if not parent_domain and missing_id_count == 0:
                        diag_parts.append(
                            "but all %s records have empty '%s' field"
                            % (total_in_model, id_field)
                        )

                diag_msg = "No parent records found for detail sync. " + "; ".join(diag_parts)
                _logger.warning("Detail sync diagnostic: %s", diag_msg)
                rec.write({
                    'detail_last_sync_at': fields.Datetime.now(),
                    'detail_last_sync_status': 'error',
                    'detail_last_sync_message': diag_msg,
                    'detail_last_sync_count': 0,
                })
                self.env.cr.commit()
                return

            # Identify parents that already have child records (skip them)
            already_synced = set()
            if detail_link_field and detail_link_field in detail_fields:
                all_pids = list(set(pid for pid, _ in parent_list))
                for i in range(0, len(all_pids), 1000):
                    batch = all_pids[i:i + 1000]
                    existing = detail_model.search_read(
                        [(detail_link_field, 'in', batch)],
                        [detail_link_field],
                    )
                    for e in existing:
                        already_synced.add(str(e[detail_link_field]))

            to_fetch = [
                (pid, parent) for pid, parent in parent_list
                if pid not in already_synced
            ]
            total_skipped = len(parent_list) - len(to_fetch)

            _logger.info(
                "Detail sync: total=%s already_synced=%s to_fetch=%s",
                len(parent_list), total_skipped, len(to_fetch),
            )
            rec.write({
                'detail_last_sync_message': (
                    "Scanning… %s parents, %s already synced, %s to fetch"
                    % (len(parent_list), total_skipped, len(to_fetch))
                ),
            })
            self.env.cr.commit()

            # ------ Per-record fetch loop ------
            for idx, (pid, parent) in enumerate(to_fetch):
                try:
                    url = rec.detail_url_pattern.replace('{id}', str(pid))
                    # Retry on 429 (rate limit)
                    for attempt in range(4):
                        try:
                            payload, _raw = rec._fetch_json(url)
                            break
                        except Exception as fetch_err:
                            if '429' in str(fetch_err) and attempt < 3:
                                wait = 5 * (attempt + 1)
                                _logger.warning(
                                    "Detail sync rate limited for %s, waiting %ss (attempt %s)",
                                    pid, wait, attempt + 1,
                                )
                                time.sleep(wait)
                                continue
                            raise
                    total_fetched += 1

                    # Dump raw JSON if enabled
                    if rec.dump_json and _raw:
                        rec._dump_raw_json(_raw, f"detail_{pid}")

                    # Resolve detail_data_root_key (dot-notation)
                    parent_context, items = rec._extract_detail_items(payload)

                    if not items:
                        _logger.debug(
                            "Detail sync: no items for parent %s", pid,
                        )
                    else:
                        try:
                            with self.env.cr.savepoint():
                                page_created, page_updated, page_errors = (
                                    rec._upsert_detail_items(
                                        items, parent_context, mapping,
                                        detail_model, detail_fields,
                                    )
                                )
                                total_created += page_created
                                total_updated += page_updated
                                total_errors += page_errors
                        except Exception as upsert_err:
                            total_errors += 1
                            _logger.warning(
                                "Detail upsert error for parent %s: %s",
                                pid, str(upsert_err)[:300],
                            )

                except Exception as e:
                    total_errors += 1
                    _logger.warning(
                        "Detail fetch error for parent %s: %s",
                        pid, str(e)[:300],
                    )

                # Progress update & commit every 5 records
                if (idx + 1) % 5 == 0 or idx == len(to_fetch) - 1:
                    try:
                        rec.write({
                            'detail_last_sync_message': (
                                "Progress: %s/%s fetched, %s created, "
                                "%s updated, %s errors"
                                % (
                                    idx + 1, len(to_fetch),
                                    total_created, total_updated, total_errors,
                                )
                            ),
                            'detail_last_sync_count': total_created + total_updated,
                        })
                    except Exception:
                        self.env.cr.rollback()
                self.env.cr.commit()

                if rec.detail_request_delay:
                    time.sleep(rec.detail_request_delay)

            # ------ Done ------
            msg = (
                "Done – Fetched: %s, Created: %s, Updated: %s, "
                "Skipped (already synced): %s, Errors: %s"
                % (
                    total_fetched, total_created, total_updated,
                    total_skipped, total_errors,
                )
            )
            rec.write({
                'detail_last_sync_at': fields.Datetime.now(),
                'detail_last_sync_status': 'ok',
                'detail_last_sync_message': msg,
                'detail_last_sync_count': total_created + total_updated,
            })
            self.env.cr.commit()
            _logger.info("Detail sync done: source=%s %s", rec.name, msg)

        except Exception as exc:
            _logger.exception(
                "Detail sync failed: source=%s error=%s",
                rec.name, str(exc),
            )
            try:
                self.env.cr.rollback()
                rec.write({
                    'detail_last_sync_at': fields.Datetime.now(),
                    'detail_last_sync_status': 'error',
                    'detail_last_sync_message': (
                        "Created: %s, Updated: %s, Errors: %s\nError: %s"
                        % (total_created, total_updated, total_errors,
                           str(exc)[:500])
                    ),
                })
                self.env.cr.commit()
            except Exception:
                _logger.exception(
                    "Failed to write detail sync error status for %s",
                    rec.name,
                )

    def _extract_detail_items(self, payload):
        """Resolve detail_data_root_key (dot-notation) and return
        (parent_context_dict, items_list).

        For ``detail_data_root_key = 'order.products'`` and payload::

            {"order": {"id": 1, "products": [...]}}

        Returns ``({"id": 1, "products": [...]}, [...])``
        so the mapping can reference both ``parent:id`` and item fields.
        """
        root_key = (self.detail_data_root_key or '').strip()
        if not root_key:
            # No root key – payload IS the list (or wraps it)
            if isinstance(payload, list):
                return {}, payload
            if isinstance(payload, dict):
                for key in ('data', 'items', 'products', 'results'):
                    val = payload.get(key)
                    if isinstance(val, list):
                        return payload, val
            return payload if isinstance(payload, dict) else {}, []

        parts = root_key.split('.')
        # Navigate to the PARENT of the items list
        context = payload
        for part in parts[:-1]:
            if isinstance(context, dict):
                context = context.get(part, {})
            else:
                return {}, []
        parent_context = context if isinstance(context, dict) else {}

        # Get the items list from the last key
        items = []
        last_part = parts[-1]
        if isinstance(parent_context, dict):
            val = parent_context.get(last_part)
            if isinstance(val, list):
                items = val
        return parent_context, items

    def _upsert_detail_items(self, items, parent_context, mapping,
                             detail_model, detail_fields):
        """Map, dedup, and upsert a list of detail items.
        Returns (created, updated, errors)."""
        created = 0
        updated = 0
        errors = 0
        unique_field = (self.detail_unique_field or '').strip()

        for item in items:
            if not isinstance(item, dict):
                continue
            values = self._map_detail_item(
                item, parent_context, mapping, detail_fields,
            )
            if not values:
                continue

            # Upsert logic
            if unique_field and unique_field in values:
                unique_val = values.get(unique_field)
                if unique_val:
                    existing = detail_model.search(
                        [(unique_field, '=', unique_val)], limit=1,
                    )
                    if existing:
                        try:
                            with self.env.cr.savepoint():
                                existing.write(values)
                                updated += 1
                        except Exception as e:
                            errors += 1
                            _logger.warning(
                                "Detail update error: %s", str(e)[:200],
                            )
                        continue

            # Create
            try:
                with self.env.cr.savepoint():
                    detail_model.create([values])
                    created += 1
            except Exception as e:
                errors += 1
                _logger.warning(
                    "Detail create error: %s", str(e)[:200],
                )

        return created, updated, errors

    def _map_detail_item(self, item, parent_context, mapping, detail_fields):
        """Map a single detail item dict to Odoo field values.

        Supports:
          - ``"field": "source_key"``       – from the item dict
          - ``"field": "parent:key"``        – from parent_context
          - ``"field": "parent:nested.key"`` – dot-notation on parent
          - ``"field": "a.b.c"``             – dot-notation on the item
          - ``"field": {"const": "value"}``  – static constant
          - ``"field": "const:value"``        – static constant shorthand
        """
        values = {}
        for target_field, source_key in mapping.items():
            if target_field not in detail_fields:
                continue
            raw_val = None
            if isinstance(source_key, dict) and 'const' in source_key:
                raw_val = source_key['const']
            elif isinstance(source_key, str) and source_key.startswith('const:'):
                raw_val = source_key.split('const:', 1)[1]
            elif isinstance(source_key, str) and source_key.startswith('parent:'):
                parent_key = source_key.split('parent:', 1)[1]
                if '.' in parent_key:
                    raw_val = self._resolve_dotted_key(
                        parent_context, parent_key,
                    )
                else:
                    raw_val = parent_context.get(parent_key)
            elif isinstance(source_key, str) and '.' in source_key:
                raw_val = self._resolve_dotted_key(item, source_key)
            elif isinstance(source_key, str):
                raw_val = item.get(source_key)
            if raw_val is not None:
                values[target_field] = self._coerce_value(
                    target_field, raw_val, detail_fields,
                )
        return values

    # ------------------------------------------------------------------
    #  Build Product Catalog from Order Details
    #  For stores where the Products API is unavailable (e.g. Zid
    #  donation stores), this extracts unique products from synced
    #  order detail records and creates mysdb.product entries.
    # ------------------------------------------------------------------
    def action_build_product_catalog(self):
        """Create mysdb.product records from unique products in order details."""
        rec = self.ensure_one()

        # Determine store_id: from detail parent domain or mapping const
        store_id = None
        if rec.detail_parent_domain:
            try:
                domain = json.loads(rec.detail_parent_domain)
                for clause in domain:
                    if (
                        isinstance(clause, (list, tuple))
                        and len(clause) >= 3
                        and clause[0] == 'store_id'
                        and clause[1] == '='
                    ):
                        store_id = str(clause[2])
                        break
            except Exception:
                pass
        if not store_id:
            # Try to get from the mapping const
            mapping = rec.mapping_json or {}
            if isinstance(mapping, str):
                try:
                    mapping = json.loads(mapping)
                except Exception:
                    mapping = {}
            for _tf, sk in mapping.items():
                if isinstance(sk, dict) and sk.get('const'):
                    store_id = str(sk['const'])
                    break
                if isinstance(sk, str) and sk.startswith('const:'):
                    store_id = sk.split('const:', 1)[1]
                    break

        # Query unique products from order details
        detail_domain = []
        if store_id:
            detail_domain.append(('store_id', '=', store_id))

        detail_model = self.env['mysdb.order.detail'].sudo()
        product_model = self.env['mysdb.product'].sudo()

        # Read all unique (product_sku, product_name) combos from details
        details = detail_model.search_read(
            detail_domain,
            ['product_sku', 'product_name', 'product_id', 'store_id'],
        )
        # Build unique product map by SKU (prefer non-empty names)
        unique_map = {}  # sku -> {sku, name, product_id, store_id}
        for d in details:
            sku = (d.get('product_sku') or '').strip()
            if not sku:
                continue
            pid = d.get('product_id') or ''
            sid = d.get('store_id') or store_id or ''
            name = (d.get('product_name') or '').strip()
            key = (sku, sid)
            if key not in unique_map or (name and not unique_map[key].get('name')):
                unique_map[key] = {
                    'sku': sku,
                    'name': name,
                    'product_id_raw': str(pid) if pid else '',
                    'store_id': sid,
                }

        # Dump product catalog JSON if enabled
        if rec.dump_json and unique_map:
            dump_data = {
                'store_id': store_id,
                'total_unique_products': len(unique_map),
                'products': list(unique_map.values()),
            }
            raw_bytes = json.dumps(dump_data, ensure_ascii=False, indent=2).encode('utf-8')
            rec._dump_raw_json(raw_bytes, 'product_catalog')

        if not unique_map:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Products Found'),
                    'message': _(
                        'No order details with product SKUs found. '
                        'Please sync orders and order details first.'
                    ),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        # Find which already exist in mysdb.product
        all_skus = list(set(info['sku'] for info in unique_map.values()))
        existing_skus = set()
        for i in range(0, len(all_skus), 1000):
            batch = all_skus[i:i + 1000]
            if store_id:
                existing = product_model.search_read(
                    [('product_sku', 'in', batch), ('store_id', '=', store_id)],
                    ['product_sku'],
                )
            else:
                existing = product_model.search_read(
                    [('product_sku', 'in', batch)],
                    ['product_sku'],
                )
            for e in existing:
                existing_skus.add(e['product_sku'])

        # Create missing products
        to_create = []
        for (sku, sid), info in unique_map.items():
            if sku in existing_skus:
                continue
            vals = {
                'product_id': info['product_id_raw'] or sku,
                'product_name': info['name'] or sku,
                'product_sku': sku,
                'store_id': info['store_id'],
            }
            to_create.append(vals)
            existing_skus.add(sku)  # avoid duplicates in batch

        created = 0
        if to_create:
            try:
                product_model.create(to_create)
                created = len(to_create)
            except Exception:
                # Fall back to one-by-one
                for vals in to_create:
                    try:
                        with self.env.cr.savepoint():
                            product_model.create([vals])
                            created += 1
                    except Exception as e:
                        _logger.warning(
                            "Build catalog: failed to create product %s: %s",
                            vals.get('product_sku'), str(e)[:200],
                        )

        msg = _(
            "Product Catalog built!\n"
            "Unique products in order details: %s\n"
            "Already in catalog: %s\n"
            "Newly created: %s"
        ) % (len(unique_map), len(unique_map) - len(to_create), created)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Product Catalog Updated'),
                'message': msg,
                'type': 'success' if created > 0 else 'info',
                'sticky': True,
            },
        }

    # ------------------------------------------------------------------
    #  Public button – launches sync in a background thread so the UI
    #  does not block / timeout.
    # ------------------------------------------------------------------
    def action_clear_sync_lock(self):
        """Manually clear a stale sync lock."""
        self.write({'sync_in_progress': False, 'sync_started_at': False})
        return True

    def action_sync(self):
        """Start sync in a background thread and return immediately."""
        for rec in self:
            # Prevent concurrent syncs
            if rec.sync_in_progress:
                # Auto-clear stale locks older than 2 hours
                if rec.sync_started_at and \
                   (fields.Datetime.now() - rec.sync_started_at).total_seconds() > 7200:
                    _logger.warning(
                        "Clearing stale sync lock for %s (started %s)",
                        rec.name, rec.sync_started_at,
                    )
                    rec.write({'sync_in_progress': False, 'sync_started_at': False})
                else:
                    raise ValidationError(
                        _("Sync is already running for '%s'. "
                          "If you believe this is stuck, use the 'Clear Sync Lock' button.")
                        % rec.name
                    )
            rec.write({
                'last_sync_message': 'Sync started – running in background…',
                'last_sync_page': 0,
                'sync_in_progress': True,
                'sync_started_at': fields.Datetime.now(),
            })
        self.env.cr.commit()

        dbname = self.env.cr.dbname
        uid = self.env.uid
        rec_ids = self.ids

        t = threading.Thread(
            target=self._sync_in_background,
            args=(dbname, uid, rec_ids),
            daemon=True,
        )
        t.start()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Started'),
                'message': _('Sync is running in the background. Refresh the page to see progress.'),
                'type': 'info',
                'sticky': False,
            },
        }

    # ------------------------------------------------------------------
    #  Background worker – runs in its own thread with a fresh cursor
    # ------------------------------------------------------------------
    @classmethod
    def _sync_in_background(cls, dbname, uid, rec_ids):
        """Execute the actual sync in a new cursor / environment."""
        try:
            registry = odoo.registry(dbname)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, uid, {})
                sources = env['mysdb.api.source'].browse(rec_ids).exists()
                for rec in sources:
                    try:
                        rec._do_sync()
                    finally:
                        # Only release lock if cursor is still alive
                        if not rec._is_cursor_dead():
                            rec._release_sync_lock()
                if not cls._check_cursor_dead(cr):
                    cr.commit()
        except Exception as e:
            _logger.exception("Background API sync thread crashed (ids=%s)", rec_ids)
            # Release lock & write status with a FRESH cursor
            cls._cleanup_after_crash(dbname, uid, rec_ids, e)

    @classmethod
    def _cleanup_after_crash(cls, dbname, uid, rec_ids, error):
        """Open a fresh cursor to release lock and write status after a crash."""
        try:
            registry = odoo.registry(dbname)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, uid, {})
                sources = env['mysdb.api.source'].browse(rec_ids).exists()
                for rec in sources:
                    rec.write({
                        'sync_in_progress': False,
                        'sync_started_at': False,
                        'last_sync_status': 'error',
                        'last_sync_message': (
                            "Sync interrupted (connection/cursor lost at page %s). "
                            "Data committed up to the previous page is safe. "
                            "Error: %s"
                            % (rec.last_sync_page or '?', str(error)[:300])
                        ),
                    })
                cr.commit()
        except Exception:
            _logger.exception("Failed to release sync lock after crash (ids=%s)", rec_ids)

    @staticmethod
    def _check_cursor_dead(cr):
        """Check if a raw cursor is dead (closed/unusable)."""
        try:
            cr.execute("SELECT 1")
            return False
        except Exception:
            return True

    def _is_cursor_dead(self):
        """Check if self.env.cr is dead (closed/unusable)."""
        try:
            self.env.cr.execute("SELECT 1")
            return False
        except Exception:
            return True

    # ------------------------------------------------------------------
    #  Core sync logic (runs inside a dedicated cursor)
    # ------------------------------------------------------------------
    def _acquire_sync_lock(self):
        """Try to acquire sync lock. Returns True if acquired, False if already locked."""
        try:
            self.env.cr.execute(
                "SELECT sync_in_progress, sync_started_at FROM mysdb_api_source WHERE id = %s FOR UPDATE NOWAIT",
                (self.id,)
            )
        except Exception:
            # Another transaction holds the row lock – skip
            _logger.info(
                "Skipping sync for %s – row is locked by another transaction",
                self.name,
            )
            self.env.cr.rollback()
            return False
        row = self.env.cr.fetchone()
        if row and row[0]:  # sync_in_progress is True
            started = row[1]
            if started and (fields.Datetime.now() - started).total_seconds() > 7200:
                _logger.warning(
                    "Clearing stale sync lock for %s (started %s)",
                    self.name, started,
                )
                # Fall through to acquire the lock
            else:
                _logger.warning(
                    "Skipping sync for %s – already in progress since %s",
                    self.name, started,
                )
                # Release the FOR UPDATE row lock so we don't block the running sync
                self.env.cr.commit()
                return False
        self.write({'sync_in_progress': True, 'sync_started_at': fields.Datetime.now()})
        self.env.cr.commit()
        return True

    def _release_sync_lock(self):
        """Release the sync lock."""
        try:
            self.write({'sync_in_progress': False, 'sync_started_at': False})
            self.env.cr.commit()
        except Exception:
            _logger.warning("Release lock ORM write failed for %s, trying raw SQL", self.name)
            try:
                self.env.cr.rollback()
                self.env.cr.execute(
                    "UPDATE mysdb_api_source SET sync_in_progress = FALSE, "
                    "sync_started_at = NULL WHERE id = %s",
                    (self.id,)
                )
                self.env.cr.commit()
            except Exception:
                _logger.exception("Failed to release sync lock for %s (even via SQL)", self.name)
                try:
                    self.env.cr.rollback()
                except Exception:
                    pass

    def _do_sync(self):
        """Perform full sync for a single API source record."""
        rec = self
        total_created = 0
        total_updated = 0
        page = rec.pagination_start if rec.pagination_start is not None else 1
        start_page = page

        try:
            _logger.info(
                "API Sync start: source=%s model=%s pagination=%s start_page=%s page_size=%s",
                rec.name,
                rec.target_model_id.model if rec.target_model_id else None,
                rec.enable_pagination,
                rec.pagination_start,
                rec.page_size,
            )
            empty_pages = 0
            prev_page_ids = set()  # for loop detection
            sync_start_time = time.time()
            estimated_total_pages = None  # discovered from API response

            while True:
                url = rec._build_request_url(page=page)
                _logger.info("API Sync page start: source=%s page=%s url=%s", rec.name, page, url)
                payload, raw = rec._fetch_json(url)
                if rec.dump_json:
                    rec._dump_raw_json(raw, page)
                items = rec._extract_items(payload)

                # --- Discover total pages from API response (first page or whenever available) ---
                if estimated_total_pages is None and isinstance(payload, dict):
                    api_total_pages, api_total_records = self._extract_pagination_meta(payload)
                    if api_total_pages and api_total_pages > 0:
                        estimated_total_pages = api_total_pages
                        _logger.info(
                            "API Sync discovered total_pages=%s for source=%s",
                            estimated_total_pages, rec.name,
                        )
                    elif api_total_records and api_total_records > 0 and rec.page_size:
                        estimated_total_pages = -(-api_total_records // rec.page_size)  # ceil division
                        _logger.info(
                            "API Sync estimated total_pages=%s from total_records=%s page_size=%s for source=%s",
                            estimated_total_pages, api_total_records, rec.page_size, rec.name,
                        )

                # --- Loop / duplicate-page detection ---
                # Build a fingerprint set from the IDs in this page.
                current_page_ids = set()
                for item in items:
                    if isinstance(item, dict):
                        item_id = item.get('id') or item.get('ID')
                        if item_id is not None:
                            current_page_ids.add(item_id)
                if (
                    current_page_ids
                    and prev_page_ids
                    and current_page_ids == prev_page_ids
                ):
                    _logger.warning(
                        "API Sync loop detected: source=%s page=%s returned same IDs as previous page. Stopping.",
                        rec.name, page,
                    )
                    break
                prev_page_ids = current_page_ids

                page_created = 0
                page_updated = 0
                try:
                    with self.env.cr.savepoint():
                        page_created, page_updated = rec._upsert_items(items)
                        total_created += page_created
                        total_updated += page_updated
                except Exception as page_err:
                    _logger.warning(
                        "API Sync page %s upsert error (recovering): %s",
                        page, str(page_err)[:300],
                    )
                    # If cursor is dead, stop immediately
                    if self._is_cursor_dead():
                        _logger.warning("Cursor died at page %s, stopping sync", page)
                        break

                # ----------------------------------------------------------
                # Commit upserted DATA first (separate from progress write).
                # This ensures data is persisted even if the progress
                # write hits a serialization error from a concurrent update.
                # ----------------------------------------------------------
                try:
                    self.env.cr.commit()
                except Exception as data_commit_err:
                    _logger.warning(
                        "API Sync page %s data commit failed (recovering): %s",
                        page, str(data_commit_err)[:200],
                    )
                    # If cursor/connection is dead, stop the sync immediately.
                    # No point in trying more pages – the caller will handle
                    # lock release & status with a fresh cursor.
                    if self._is_cursor_dead():
                        _logger.warning("Cursor died at page %s, stopping sync", page)
                        break
                    try:
                        self.env.cr.rollback()
                    except Exception:
                        pass

                # ----------------------------------------------------------
                # Progress update – non-critical, in its own mini-transaction.
                # If this fails (e.g. concurrent update), we just skip it and
                # continue to the next page.
                # ----------------------------------------------------------
                if not self._is_cursor_dead():
                    # --- Build progress message with ETA ---
                    pages_done = page - start_page + 1
                    elapsed = time.time() - sync_start_time
                    avg_per_page = elapsed / pages_done if pages_done > 0 else 0

                    if estimated_total_pages and estimated_total_pages > 0:
                        pages_remaining = max(0, estimated_total_pages - page)
                        eta_seconds = pages_remaining * avg_per_page
                        progress_pct = min(100, int(page / estimated_total_pages * 100))
                        progress_msg = (
                            "Running… page %s/%s (%s%%) | created %s | updated %s | "
                            "elapsed %s | ETA %s"
                            % (
                                page, estimated_total_pages, progress_pct,
                                total_created, total_updated,
                                self._format_eta(elapsed),
                                self._format_eta(eta_seconds),
                            )
                        )
                    else:
                        progress_msg = (
                            "Running… page %s | created %s | updated %s | "
                            "elapsed %s | ~%s/page"
                            % (
                                page, total_created, total_updated,
                                self._format_eta(elapsed),
                                self._format_eta(avg_per_page),
                            )
                        )

                    try:
                        rec.write({
                            'last_sync_page': page,
                            'last_sync_page_items': len(items),
                            'last_sync_page_created': page_created,
                            'last_sync_page_updated': page_updated,
                            'last_sync_message': progress_msg,
                        })
                        self.env.cr.commit()
                    except Exception:
                        _logger.debug(
                            "Progress write failed for page %s (concurrent update?), continuing",
                            page,
                        )
                        if self._is_cursor_dead():
                            _logger.warning("Cursor died at page %s during progress write, stopping", page)
                            break
                        try:
                            self.env.cr.rollback()
                        except Exception:
                            pass

                _logger.info(
                    "API Sync page done: source=%s page=%s items=%s created=%s updated=%s running_total=%s",
                    rec.name,
                    page,
                    len(items),
                    page_created,
                    page_updated,
                    total_created + total_updated,
                )

                if not rec.enable_pagination:
                    _logger.info("API Sync finished (no pagination): source=%s page=%s", rec.name, page)
                    break
                if not items:
                    empty_pages += 1
                    if empty_pages >= 3:
                        _logger.info(
                            "API Sync finished after %s empty pages: source=%s page=%s",
                            empty_pages, rec.name, page,
                        )
                        break
                else:
                    empty_pages = 0
                page += 1

                # Rate limiting: wait between page requests
                if rec.page_request_delay and rec.page_request_delay > 0:
                    time.sleep(rec.page_request_delay)

            total_elapsed = time.time() - sync_start_time
            msg = "Done – Created: %s, Updated: %s (pages: %s) in %s" % (
                total_created, total_updated, page,
                self._format_eta(total_elapsed),
            )
            # Write final status. Lock release is handled by the CALLER
            # (_sync_in_background / cron_auto_sync_all), not here.
            if self._is_cursor_dead():
                _logger.info(
                    "API Sync completed page loop but cursor is dead, skipping final status write: %s",
                    msg,
                )
                return
            try:
                rec.write({
                    'last_sync_at': fields.Datetime.now(),
                    'last_sync_status': 'ok',
                    'last_sync_message': msg,
                    'last_sync_count': total_created + total_updated,
                    'last_sync_page': page,
                })
                self.env.cr.commit()
            except Exception:
                _logger.warning(
                    "Final status write failed for %s (concurrent update?), retrying after rollback",
                    rec.name,
                )
                if self._is_cursor_dead():
                    return
                try:
                    self.env.cr.rollback()
                    rec.write({
                        'last_sync_at': fields.Datetime.now(),
                        'last_sync_status': 'ok',
                        'last_sync_message': msg,
                        'last_sync_count': total_created + total_updated,
                    })
                    self.env.cr.commit()
                except Exception:
                    _logger.warning("Retry of final status write also failed for %s", rec.name)
                    try:
                        self.env.cr.rollback()
                    except Exception:
                        pass
            try:
                self.env['mysdb.sync.log'].sudo().create({
                    'source_type': 'api',
                    'source_name': rec.name,
                    'sync_datetime': fields.Datetime.now(),
                    'sync_status': 'ok',
                    'sync_message': msg,
                })
                self.env.cr.commit()
            except Exception:
                _logger.debug("Sync log write failed for %s", rec.name)
                try:
                    self.env.cr.rollback()
                except Exception:
                    pass

        except Exception as exc:
            _logger.exception("API Sync failed: source=%s error=%s", rec.name, str(exc))
            # If cursor is dead, skip all writes – the caller (_sync_in_background
            # or cron_auto_sync_all) will handle status/lock with a fresh cursor.
            if self._is_cursor_dead():
                _logger.warning(
                    "Cursor is dead, skipping status write for %s (caller will handle)",
                    rec.name,
                )
                return
            # Write error status. Lock release is handled by the CALLER.
            try:
                self.env.cr.rollback()
                rec.write({
                    'last_sync_at': fields.Datetime.now(),
                    'last_sync_status': 'error',
                    'last_sync_message': (
                        "Created: %s, Updated: %s, Last page: %s\nError: %s"
                        % (total_created, total_updated, page, str(exc)[:500])
                    ),
                    'last_sync_count': total_created + total_updated,
                })
                self.env.cr.commit()
            except Exception:
                _logger.exception("Failed to write error status for API source %s", rec.name)
                try:
                    self.env.cr.rollback()
                except Exception:
                    pass
            try:
                self.env['mysdb.sync.log'].sudo().create({
                    'source_type': 'api',
                    'source_name': rec.name,
                    'sync_datetime': fields.Datetime.now(),
                    'sync_status': 'error',
                    'sync_message': str(exc)[:1000],
                })
                self.env.cr.commit()
            except Exception:
                _logger.debug("Failed to write sync log for API source %s", rec.name)
                try:
                    self.env.cr.rollback()
                except Exception:
                    pass

    def _compute_next_run(self):
        """Calculate the next auto-sync run time based on interval settings."""
        now = fields.Datetime.now()
        interval = self.auto_sync_interval or 1
        interval_type = self.auto_sync_interval_type or 'hours'
        if interval_type == 'minutes':
            delta = timedelta(minutes=interval)
        elif interval_type == 'days':
            delta = timedelta(days=interval)
        else:
            delta = timedelta(hours=interval)
        self.write({'auto_sync_next_run': now + delta})

    @api.model
    def cron_auto_sync_all(self):
        """Called by scheduled action to sync API sources whose next_run is due.

        For each source:
        1. Check if it's time to run (next_run <= now, or next_run not set)
        2. Sync main records (orders / products / etc.)
        3. If detail_sync_enabled, also sync child records (order details)
        4. Calculate next_run based on the source's interval settings
        """
        now = fields.Datetime.now()
        sources = self.search([
            ('auto_sync', '=', True),
            ('active', '=', True),
            '|',
            ('auto_sync_next_run', '=', False),
            ('auto_sync_next_run', '<=', now),
        ])
        if not sources:
            _logger.info("Auto-sync: no API sources due for sync at %s", now)
            return

        for src in sources:
            _logger.info(
                "Auto-sync starting for API source: %s (next_run was %s)",
                src.name, src.auto_sync_next_run,
            )

            # --- Acquire lock (skip if already running) ---
            try:
                if not src._acquire_sync_lock():
                    _logger.info("Auto-sync skipped for %s – already in progress", src.name)
                    continue
            except Exception:
                _logger.warning("Auto-sync could not acquire lock for %s", src.name)
                continue

            try:
                # --- Step 1: main sync ---
                try:
                    src._do_sync()
                    _logger.info("Auto-sync completed for API source: %s", src.name)
                except Exception as e:
                    _logger.error("Auto-sync failed for API source %s: %s", src.name, str(e))
                    if self._is_cursor_dead():
                        _logger.warning("Auto-sync cursor died for %s, aborting remaining sources", src.name)
                        return
                    src._compute_next_run()
                    src._release_sync_lock()
                    self.env.cr.commit()
                    continue  # skip detail sync if main sync crashed

                # --- Step 2: detail sync (if enabled) ---
                if src.detail_sync_enabled:
                    try:
                        src._do_sync_details()
                        _logger.info(
                            "Auto detail-sync completed for API source: %s",
                            src.name,
                        )
                    except Exception as e:
                        _logger.error(
                            "Auto detail-sync failed for API source %s: %s",
                            src.name, str(e),
                        )

                # --- Step 3: schedule next run & release lock ---
                if not self._is_cursor_dead():
                    src._compute_next_run()
                    src._release_sync_lock()
                    self.env.cr.commit()
                else:
                    _logger.warning("Auto-sync cursor died for %s after sync", src.name)
                    return

            except Exception as e:
                _logger.exception("Auto-sync unexpected error for %s: %s", src.name, str(e))
                if not self._is_cursor_dead():
                    src._release_sync_lock()
                    self.env.cr.commit()

    # ------------------------------------------------------------------
    #  Deduplicate – remove duplicate records based on unique field
    # ------------------------------------------------------------------
    def action_deduplicate(self):
        """Remove duplicate records from the target model based on the
        configured unique field.  Keeps the OLDEST record (lowest id)
        and deletes the newer duplicates.

        Also deduplicates mysdb.order.detail when the target model is
        mysdb.order.
        """
        rec = self.ensure_one()
        if not rec.target_model_id:
            raise ValidationError(_("No target model configured."))

        unique_fields = []
        if rec.unique_field:
            model = self.env[rec.target_model_id.model].sudo()
            unique_fields = [
                f.strip()
                for f in str(rec.unique_field).replace(';', ',').split(',')
                if f.strip() and f.strip() in model._fields
            ]

        if not unique_fields:
            raise ValidationError(
                _("Cannot deduplicate without a Unique Field. "
                  "Please set the Unique Field first.")
            )

        model_name = rec.target_model_id.model
        table_name = model_name.replace('.', '_')

        # Build SQL to find duplicates — keep the record with the lowest id
        if len(unique_fields) == 1:
            field = unique_fields[0]
            count_sql = """
                SELECT {field}, COUNT(*) as cnt
                FROM {table}
                WHERE {field} IS NOT NULL AND {field} != ''
                GROUP BY {field}
                HAVING COUNT(*) > 1
            """.format(field=field, table=table_name)
            self.env.cr.execute(count_sql)
            dups = self.env.cr.fetchall()
            total_dup_groups = len(dups)
            total_extra = sum(row[1] - 1 for row in dups)

            if total_extra == 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Duplicates'),
                        'message': _('No duplicate records found in %s.') % model_name,
                        'type': 'info',
                        'sticky': False,
                    },
                }

            # Delete duplicates (keep lowest id per unique value)
            delete_sql = """
                DELETE FROM {table}
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM {table}
                    WHERE {field} IS NOT NULL AND {field} != ''
                    GROUP BY {field}
                )
                AND {field} IN (
                    SELECT {field}
                    FROM {table}
                    WHERE {field} IS NOT NULL AND {field} != ''
                    GROUP BY {field}
                    HAVING COUNT(*) > 1
                )
            """.format(field=field, table=table_name)
        else:
            # Multiple unique fields
            field_list = ', '.join(unique_fields)
            where_not_null = ' AND '.join(
                f"{f} IS NOT NULL AND {f} != ''" for f in unique_fields
            )
            count_sql = """
                SELECT {fields}, COUNT(*) as cnt
                FROM {table}
                WHERE {where}
                GROUP BY {fields}
                HAVING COUNT(*) > 1
            """.format(fields=field_list, table=table_name, where=where_not_null)
            self.env.cr.execute(count_sql)
            dups = self.env.cr.fetchall()
            total_dup_groups = len(dups)
            total_extra = sum(row[-1] - 1 for row in dups)

            if total_extra == 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Duplicates'),
                        'message': _('No duplicate records found in %s.') % model_name,
                        'type': 'info',
                        'sticky': False,
                    },
                }

            delete_sql = """
                DELETE FROM {table}
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM {table}
                    WHERE {where}
                    GROUP BY {fields}
                )
                AND id IN (
                    SELECT t.id FROM {table} t
                    INNER JOIN (
                        SELECT {fields}
                        FROM {table}
                        WHERE {where}
                        GROUP BY {fields}
                        HAVING COUNT(*) > 1
                    ) d ON {join_cond}
                )
            """.format(
                fields=field_list,
                table=table_name,
                where=where_not_null,
                join_cond=' AND '.join(f"t.{f} = d.{f}" for f in unique_fields),
            )

        _logger.info(
            "Dedup: source=%s model=%s dup_groups=%s extra_records=%s",
            rec.name, model_name, total_dup_groups, total_extra,
        )
        self.env.cr.execute(delete_sql)
        deleted = self.env.cr.rowcount
        _logger.info("Dedup: deleted %s duplicate records from %s", deleted, model_name)

        # Also dedup order details if target is mysdb.order
        detail_deleted = 0
        if model_name == 'mysdb.order':
            detail_deleted = self._deduplicate_order_details()

        self.env.cr.commit()

        # Invalidate ORM cache since we used raw SQL
        self.env[model_name].invalidate_model()
        if model_name == 'mysdb.order':
            self.env['mysdb.order.detail'].invalidate_model()

        msg = _(
            "Deduplication complete!\n"
            "• %s: %s duplicate groups found, %s extra records deleted\n"
        ) % (model_name, total_dup_groups, deleted)
        if detail_deleted:
            msg += _("• mysdb.order.detail: %s duplicate records deleted\n") % detail_deleted

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deduplication Done'),
                'message': msg,
                'type': 'success',
                'sticky': True,
            },
        }

    def _deduplicate_order_details(self):
        """Remove duplicate order detail records.
        Keeps oldest record per (order_linked_id, product_name, product_sku, store_id)."""
        self.env.cr.execute("""
            DELETE FROM mysdb_order_detail
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM mysdb_order_detail
                WHERE order_linked_id IS NOT NULL
                GROUP BY order_linked_id, product_name, product_sku, store_id
            )
            AND order_linked_id IS NOT NULL
            AND id IN (
                SELECT d.id FROM mysdb_order_detail d
                INNER JOIN (
                    SELECT order_linked_id, product_name, product_sku, store_id
                    FROM mysdb_order_detail
                    WHERE order_linked_id IS NOT NULL
                    GROUP BY order_linked_id, product_name, product_sku, store_id
                    HAVING COUNT(*) > 1
                ) dup ON d.order_linked_id = dup.order_linked_id
                    AND (d.product_name = dup.product_name OR (d.product_name IS NULL AND dup.product_name IS NULL))
                    AND (d.product_sku = dup.product_sku OR (d.product_sku IS NULL AND dup.product_sku IS NULL))
                    AND (d.store_id = dup.store_id OR (d.store_id IS NULL AND dup.store_id IS NULL))
            )
        """)
        deleted = self.env.cr.rowcount
        _logger.info("Dedup order details: deleted %s duplicates", deleted)
        return deleted

    def _dump_raw_json(self, raw, page):
        base_dir = (self.dump_directory or '').replace('\u00A0', ' ').strip().strip('"')
        if not base_dir:
            base_dir = os.path.join(config.get('data_dir') or '.', 'api_dumps')
        if base_dir and os.path.splitext(base_dir)[1]:
            base_dir = os.path.dirname(base_dir)
        base_dir = os.path.normpath(base_dir)
        if os.path.exists(base_dir) and not os.path.isdir(base_dir):
            _logger.warning("Dump Directory is not a folder, falling back: %s", base_dir)
            base_dir = os.path.join(config.get('data_dir') or '.', 'api_dumps')
        if not os.path.isdir(base_dir):
            try:
                os.makedirs(base_dir, exist_ok=True)
            except Exception as exc:
                _logger.warning("Dump directory create failed (%s): %s", base_dir, str(exc))
                base_dir = os.path.join(config.get('data_dir') or '.', 'api_dumps')
                os.makedirs(base_dir, exist_ok=True)
        safe_name = self._safe_filename(self.name or 'source')
        prefix = self._safe_filename(self.dump_file_prefix or 'api_dump')
        timestamp = fields.Datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{prefix}_{safe_name}_page{page}_{timestamp}.json"
        full_path = os.path.join(base_dir, filename)
        try:
            with open(full_path, 'wb') as handle:
                handle.write(raw)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            self.last_dump_file = full_path
            self.last_dump_size = size
            _logger.info("Dump written: %s (%s bytes)", full_path, size)
        except Exception as exc:
            _logger.warning("Dump write failed (%s): %s", full_path, str(exc))

    def _safe_filename(self, value):
        value = value or ''
        value = re.sub(r'[^A-Za-z0-9._-]+', '_', value)
        return value.strip('_') or 'file'

