# -*- coding: utf-8 -*-
import csv
import io
import json
import logging
import re
import urllib.request

from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from .mysdb_date_utils import normalize_datetime as _normalize_dt, normalize_date as _normalize_d

_logger = logging.getLogger(__name__)


MAX_SHEET_COLUMNS = 25


def _col_field_name(idx):
    return f"col_{idx:02d}"


def _tag_field_name(idx):
    return f"tag_{idx:02d}"


def _type_field_name(idx):
    return f"type_{idx:02d}"


class MysdbSheetSource(models.Model):
    _name = 'mysdb.sheet.source'
    _description = 'MySDB Google Sheet Source'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    spreadsheet_id = fields.Char(string='Spreadsheet ID', required=True)
    worksheet_gid = fields.Char(string='Worksheet GID', default='0')
    worksheet_name = fields.Char(string='Worksheet Name')
    auth_type = fields.Selection(
        [('public', 'Public (CSV)'), ('service', 'Service Account')],
        string='Auth Type',
        default='public',
        required=True
    )
    service_account_json = fields.Text(string='Service Account JSON')
    service_account_scopes = fields.Char(
        string='Service Account Scopes',
        default='https://www.googleapis.com/auth/spreadsheets.readonly',
        help='Comma-separated scopes for service account access.'
    )
    sync_to_model = fields.Boolean(string='Sync to Target Model', default=False)
    delete_missing_rows = fields.Boolean(
        string='Delete Missing Rows',
        default=False,
        help='If enabled, rows removed from the sheet will be deleted from Sheet Rows.'
    )
    target_model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        domain="[('model', '=ilike', 'mysdb.%')]",
        ondelete='set null'
    )
    unique_field = fields.Char(
        string='Unique Field',
        help="Field used to upsert (e.g. product_id). Leave empty to always create."
    )
    mapping_json = fields.Json(
        string='Field Mapping',
        help=(
            "JSON mapping of target_field -> sheet column name. "
            "Example: {'product_id':'Project ID','store_id':{'const':'123'}}. "
            "You may also use 'const:123'."
        )
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        help='Company that owns this sheet source. Leave empty for shared access.'
    )
    auto_sync = fields.Boolean(
        string='Auto Sync', default=False,
        help='If enabled, this sheet source will be synced automatically by the system scheduler.'
    )

    last_sync_at = fields.Datetime(string='Last Sync At', readonly=True)
    last_sync_status = fields.Selection(
        [('ok', 'OK'), ('error', 'Error')],
        string='Last Sync Status',
        readonly=True
    )
    last_sync_message = fields.Text(string='Last Sync Message', readonly=True)
    last_sync_count = fields.Integer(string='Last Sync Count', readonly=True)

    # Column tags + types (mapping config)
    tag_01 = fields.Char(string='Tag 01')
    tag_02 = fields.Char(string='Tag 02')
    tag_03 = fields.Char(string='Tag 03')
    tag_04 = fields.Char(string='Tag 04')
    tag_05 = fields.Char(string='Tag 05')
    tag_06 = fields.Char(string='Tag 06')
    tag_07 = fields.Char(string='Tag 07')
    tag_08 = fields.Char(string='Tag 08')
    tag_09 = fields.Char(string='Tag 09')
    tag_10 = fields.Char(string='Tag 10')
    tag_11 = fields.Char(string='Tag 11')
    tag_12 = fields.Char(string='Tag 12')
    tag_13 = fields.Char(string='Tag 13')
    tag_14 = fields.Char(string='Tag 14')
    tag_15 = fields.Char(string='Tag 15')
    tag_16 = fields.Char(string='Tag 16')
    tag_17 = fields.Char(string='Tag 17')
    tag_18 = fields.Char(string='Tag 18')
    tag_19 = fields.Char(string='Tag 19')
    tag_20 = fields.Char(string='Tag 20')
    tag_21 = fields.Char(string='Tag 21')
    tag_22 = fields.Char(string='Tag 22')
    tag_23 = fields.Char(string='Tag 23')
    tag_24 = fields.Char(string='Tag 24')
    tag_25 = fields.Char(string='Tag 25')

    type_01 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 01', default='text')
    type_02 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 02', default='text')
    type_03 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 03', default='text')
    type_04 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 04', default='text')
    type_05 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 05', default='text')
    type_06 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 06', default='text')
    type_07 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 07', default='text')
    type_08 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 08', default='text')
    type_09 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 09', default='text')
    type_10 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 10', default='text')
    type_11 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 11', default='text')
    type_12 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 12', default='text')
    type_13 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 13', default='text')
    type_14 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 14', default='text')
    type_15 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 15', default='text')
    type_16 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 16', default='text')
    type_17 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 17', default='text')
    type_18 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 18', default='text')
    type_19 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 19', default='text')
    type_20 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 20', default='text')
    type_21 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 21', default='text')
    type_22 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 22', default='text')
    type_23 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 23', default='text')
    type_24 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 24', default='text')
    type_25 = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('bool', 'Boolean'),
    ], string='Type 25', default='text')

    def _build_csv_url(self):
        if not self.spreadsheet_id:
            raise ValidationError(_("Spreadsheet ID is required."))
        gid = (self.worksheet_gid or '0').strip()
        return (
            "https://docs.google.com/spreadsheets/d/%s/export?format=csv&gid=%s"
            % (self.spreadsheet_id.strip(), gid)
        )

    def _get_service_account_creds(self):
        if not self.service_account_json:
            raise ValidationError(_("Service Account JSON is required for private sheets."))
        try:
            payload = json.loads(self.service_account_json)
        except Exception as exc:
            raise ValidationError(_("Invalid Service Account JSON: %s") % str(exc))
        try:
            from google.oauth2.service_account import Credentials
        except Exception as exc:
            raise ValidationError(_("Missing google-auth library: %s") % str(exc))
        scopes = [s.strip() for s in (self.service_account_scopes or '').split(',') if s.strip()]
        if not scopes:
            scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        return Credentials.from_service_account_info(payload, scopes=scopes)

    def _get_sheet_title(self, service):
        if self.worksheet_name:
            return self.worksheet_name.strip()
        gid = (self.worksheet_gid or '0').strip()
        if not gid.isdigit():
            raise ValidationError(_("Worksheet GID must be numeric."))
        try:
            spreadsheet = service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id,
                fields='sheets.properties'
            ).execute()
        except Exception as exc:
            raise ValidationError(_("Failed to read spreadsheet metadata: %s") % str(exc))
        target_id = int(gid)
        for sheet in spreadsheet.get('sheets', []):
            props = sheet.get('properties', {})
            if props.get('sheetId') == target_id:
                return props.get('title')
        raise ValidationError(_("Worksheet GID not found in spreadsheet."))

    def _fetch_csv_rows(self):
        if self.auth_type == 'service':
            try:
                from googleapiclient.discovery import build
            except Exception as exc:
                raise ValidationError(_("Missing google-api-python-client library: %s") % str(exc))
            creds = self._get_service_account_creds()
            service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
            title = self._get_sheet_title(service)
            try:
                result = service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=title
                ).execute()
            except Exception as exc:
                raise ValidationError(_("Failed to fetch sheet values: %s") % str(exc))
            values = result.get('values', [])
            return values

        url = self._build_csv_url()
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
        except Exception as exc:
            raise ValidationError(_("Failed to fetch sheet CSV: %s") % str(exc))
        try:
            text = data.decode('utf-8-sig')
            reader = csv.reader(io.StringIO(text))
            return list(reader)
        except Exception as exc:
            raise ValidationError(_("Invalid CSV response: %s") % str(exc))

    def action_fetch_columns(self):
        for rec in self:
            rows = rec._fetch_csv_rows()
            if not rows:
                raise ValidationError(_("Sheet is empty."))
            headers = rows[0]
            vals = {}
            for i in range(1, MAX_SHEET_COLUMNS + 1):
                tag_field = _tag_field_name(i)
                vals[tag_field] = headers[i - 1].strip() if i <= len(headers) else False
            rec.write(vals)

    def _normalize_cell(self, raw, col_type):
        if raw is None:
            return False, {}
        val = str(raw).strip()
        if val == '':
            return False, {}
        typed = {}
        if col_type == 'number':
            try:
                typed['num'] = float(val)
            except Exception:
                pass
        if col_type == 'integer':
            try:
                typed['int'] = int(float(val))
            except Exception:
                pass
        if col_type == 'date':
            try:
                dt = datetime.fromisoformat(val)
                typed['date'] = dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
            except Exception:
                pass
        if col_type == 'datetime':
            try:
                dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                typed['datetime'] = dt.replace(tzinfo=None).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            except Exception:
                pass
        if col_type == 'bool':
            if val.lower() in ('1', 'true', 'yes', 'y'):
                typed['bool'] = True
            if val.lower() in ('0', 'false', 'no', 'n'):
                typed['bool'] = False
        return val, typed

    def _normalize_datetime(self, value):
        """Delegate to shared date utility."""
        return _normalize_dt(value)

    def _normalize_date(self, value):
        """Delegate to shared date utility."""
        return _normalize_d(value)

    def _coerce_value(self, field_name, value, model_fields):
        field = model_fields.get(field_name)
        if not field:
            return value
        if field.type == 'many2one':
            if value in (None, False, ''):
                return False
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip().isdigit():
                return int(value.strip())
            # Try to resolve by display name or model identifier
            comodel = self.env[field.comodel_name]
            if field.comodel_name == 'ir.model':
                rec = comodel.search([('model', '=', value)], limit=1)
                if not rec:
                    rec = comodel.search([('name', '=', value)], limit=1)
                if not rec:
                    rec = comodel.search([('name', 'ilike', value)], limit=1)
                if rec:
                    return rec.id
            else:
                candidates = comodel.name_search(value, operator='ilike', limit=1)
                if candidates:
                    return candidates[0][0]
            return value
        if field.type == 'datetime' and isinstance(value, str):
            return self._normalize_datetime(value)
        if field.type == 'date' and isinstance(value, str):
            return self._normalize_date(value)
        if field.type == 'boolean' and isinstance(value, str):
            return value.lower() in ('1', 'true', 'yes', 'y')
        if field.type == 'integer' and isinstance(value, str):
            try:
                return int(value.strip())
            except Exception:
                return value
        if field.type == 'float' and isinstance(value, str):
            try:
                return float(value.strip())
            except Exception:
                return value
        return value

    def _normalize_header_key(self, key):
        if not key:
            return ''
        key = str(key).strip().lower()
        key = re.sub(r'[^a-z0-9_]+', '_', key)
        key = re.sub(r'_+', '_', key).strip('_')
        return key

    def _get_header_aliases(self, model_name):
        aliases = {}
        if model_name == 'mysdb.credential':
            aliases.update({
                'database': 'name',
                'db': 'name',
                'db_name': 'name',
                'database_name': 'name',
                'username': 'user',
                'user_name': 'user',
                'user': 'user',
                'host_name': 'host',
                'hostname': 'host',
                'server': 'host',
                'server_name': 'host',
                'connect_timeout': 'connect_timeout',
                'connection_timeout': 'connect_timeout',
                'ssl_mode': 'ssl_mode',
                'ssl_ca': 'ssl_ca',
                'ssl_cert': 'ssl_cert',
                'ssl_key': 'ssl_key',
            })
        return aliases

    def _map_row_to_values(self, raw_map, col_values, model_fields):
        mapping = self.mapping_json or {}
        if isinstance(mapping, str):
            try:
                mapping = json.loads(mapping)
            except Exception as exc:
                raise ValidationError(_("Field Mapping must be valid JSON. %s") % str(exc))
        values = {}
        normalized_raw_map = {self._normalize_header_key(k): v for k, v in raw_map.items()}
        aliases = self._get_header_aliases(self.target_model_id.model) if self.target_model_id else {}
        if mapping:
            label_to_field = {
                (field.string or '').strip().lower(): name
                for name, field in model_fields.items()
            }
            for target_field, source_key in mapping.items():
                target_field_name = target_field
                if target_field_name not in model_fields:
                    target_field_name = label_to_field.get(str(target_field).strip().lower())
                if target_field_name not in model_fields:
                    continue
                raw_val = None
                if isinstance(source_key, dict) and 'const' in source_key:
                    raw_val = source_key.get('const')
                elif isinstance(source_key, str) and source_key.startswith('const:'):
                    raw_val = source_key.split('const:', 1)[1]
                elif source_key in raw_map:
                    raw_val = raw_map.get(source_key)
                elif source_key in col_values:
                    raw_val = col_values.get(source_key)
                else:
                    normalized_key = self._normalize_header_key(source_key)
                    if normalized_key in normalized_raw_map:
                        raw_val = normalized_raw_map.get(normalized_key)
                    elif normalized_key in aliases and aliases[normalized_key] in model_fields:
                        raw_val = normalized_raw_map.get(normalized_key)
                if raw_val is not None:
                    values[target_field_name] = self._coerce_value(target_field_name, raw_val, model_fields)
        else:
            # Auto-map by sheet header names
            for key, raw_val in raw_map.items():
                if key in model_fields:
                    values[key] = self._coerce_value(key, raw_val, model_fields)
                else:
                    normalized_key = self._normalize_header_key(key)
                    if normalized_key in model_fields:
                        values[normalized_key] = self._coerce_value(normalized_key, raw_val, model_fields)
                    elif normalized_key in aliases and aliases[normalized_key] in model_fields:
                        values[aliases[normalized_key]] = self._coerce_value(
                            aliases[normalized_key], raw_val, model_fields
                        )
            # Auto-map by tag if tag matches a target field name
            for i in range(1, MAX_SHEET_COLUMNS + 1):
                tag = getattr(self, _tag_field_name(i))
                if not tag:
                    continue
                tag_key = tag if tag in model_fields else self._normalize_header_key(tag)
                if tag_key not in model_fields:
                    continue
                base = _col_field_name(i)
                raw_val = col_values.get(base)
                if raw_val is not None:
                    values[tag_key] = self._coerce_value(tag_key, raw_val, model_fields)
        return values

    def action_sync(self):
        Row = self.env['mysdb.sheet.row'].sudo()
        for rec in self:
            try:
                rows = rec._fetch_csv_rows()
                if not rows:
                    raise ValidationError(_("Sheet is empty."))
                headers = rows[0]
                header_index = {h.strip(): idx for idx, h in enumerate(headers)}

                synced = 0
                target_created = 0
                target_updated = 0
                target_skipped = 0
                seen_rows = set()
                for row_number, row in enumerate(rows[1:], start=2):
                    if not row:
                        continue
                    seen_rows.add(row_number)
                    raw_map = {}
                    for h, idx in header_index.items():
                        raw_map[h] = row[idx] if idx < len(row) else ''

                    vals = {
                        'source_id': rec.id,
                        'row_number': row_number,
                        'raw_json': json.dumps(raw_map, ensure_ascii=False),
                    }
                    col_values = {}
                    for i in range(1, MAX_SHEET_COLUMNS + 1):
                        tag = getattr(rec, _tag_field_name(i))
                        if not tag:
                            continue
                        col_type = getattr(rec, _type_field_name(i)) or 'text'
                        raw_val = raw_map.get(tag, '')
                        text_val, typed = rec._normalize_cell(raw_val, col_type)
                        base = _col_field_name(i)
                        vals[base] = text_val
                        col_values[base] = text_val
                        # Clear typed columns to avoid stale values when type changes
                        vals[f"{base}_num"] = False
                        vals[f"{base}_int"] = False
                        vals[f"{base}_date"] = False
                        vals[f"{base}_datetime"] = False
                        vals[f"{base}_bool"] = False
                        if 'num' in typed:
                            vals[f"{base}_num"] = typed['num']
                        if 'int' in typed:
                            vals[f"{base}_int"] = typed['int']
                        if 'date' in typed:
                            vals[f"{base}_date"] = typed['date']
                        if 'datetime' in typed:
                            vals[f"{base}_datetime"] = typed['datetime']
                        if 'bool' in typed:
                            vals[f"{base}_bool"] = typed['bool']

                    existing = Row.search([('source_id', '=', rec.id), ('row_number', '=', row_number)], limit=1)
                    if existing:
                        existing.write(vals)
                    else:
                        Row.create(vals)
                    synced += 1

                    if rec.sync_to_model and rec.target_model_id:
                        model = self.env[rec.target_model_id.model].sudo()
                        model_fields = model._fields
                        mapped_vals = rec._map_row_to_values(raw_map, col_values, model_fields)
                        if mapped_vals:
                            if rec.unique_field and rec.unique_field in model_fields:
                                unique_val = mapped_vals.get(rec.unique_field)
                                if unique_val:
                                    target = model.search([(rec.unique_field, '=', unique_val)], limit=1)
                                    if target:
                                        target.write(mapped_vals)
                                        target_updated += 1
                                    else:
                                        model.create(mapped_vals)
                                        target_created += 1
                                else:
                                    model.create(mapped_vals)
                                    target_created += 1
                            else:
                                model.create(mapped_vals)
                                target_created += 1
                        else:
                            target_skipped += 1

                if rec.delete_missing_rows:
                    to_delete = Row.search([
                        ('source_id', '=', rec.id),
                        ('row_number', 'not in', list(seen_rows)),
                    ])
                    if to_delete:
                        to_delete.unlink()

                message = ''
                if rec.sync_to_model and rec.target_model_id:
                    message = _(
                        "Rows: %s, Target created: %s, updated: %s, skipped: %s"
                    ) % (synced, target_created, target_updated, target_skipped)
                rec.write({
                    'last_sync_at': fields.Datetime.now(),
                    'last_sync_status': 'ok',
                    'last_sync_message': message,
                    'last_sync_count': synced,
                })
                self.env['mysdb.sync.log'].sudo().create({
                    'source_type': 'sheet',
                    'source_name': rec.name,
                    'sync_datetime': fields.Datetime.now(),
                    'sync_status': 'ok',
                    'sync_message': message,
                })
            except Exception as exc:
                rec.write({
                    'last_sync_at': fields.Datetime.now(),
                    'last_sync_status': 'error',
                    'last_sync_message': str(exc),
                    'last_sync_count': 0,
                })
                self.env['mysdb.sync.log'].sudo().create({
                    'source_type': 'sheet',
                    'source_name': rec.name,
                    'sync_datetime': fields.Datetime.now(),
                    'sync_status': 'error',
                    'sync_message': str(exc),
                })
                raise

    @api.model
    def cron_auto_sync_all(self):
        """Called by scheduled action to sync all sheet sources with auto_sync=True."""
        sources = self.search([('auto_sync', '=', True), ('active', '=', True)])
        for src in sources:
            try:
                src.action_sync()
                _logger.info("Auto-sync completed for sheet source: %s", src.name)
            except Exception as e:
                _logger.error("Auto-sync failed for sheet source %s: %s", src.name, str(e))


class MysdbSheetRow(models.Model):
    _name = 'mysdb.sheet.row'
    _description = 'MySDB Google Sheet Row'
    _rec_name = 'row_number'

    source_id = fields.Many2one('mysdb.sheet.source', string='Sheet Source', required=True, ondelete='cascade')
    row_number = fields.Integer(string='Row Number', required=True, index=True)
    raw_json = fields.Text(string='Raw JSON')
    tag_01 = fields.Char(string='Tag 01', related='source_id.tag_01', readonly=True, store=False)
    tag_02 = fields.Char(string='Tag 02', related='source_id.tag_02', readonly=True, store=False)
    tag_03 = fields.Char(string='Tag 03', related='source_id.tag_03', readonly=True, store=False)
    tag_04 = fields.Char(string='Tag 04', related='source_id.tag_04', readonly=True, store=False)
    tag_05 = fields.Char(string='Tag 05', related='source_id.tag_05', readonly=True, store=False)
    tag_06 = fields.Char(string='Tag 06', related='source_id.tag_06', readonly=True, store=False)
    tag_07 = fields.Char(string='Tag 07', related='source_id.tag_07', readonly=True, store=False)
    tag_08 = fields.Char(string='Tag 08', related='source_id.tag_08', readonly=True, store=False)
    tag_09 = fields.Char(string='Tag 09', related='source_id.tag_09', readonly=True, store=False)
    tag_10 = fields.Char(string='Tag 10', related='source_id.tag_10', readonly=True, store=False)
    tag_11 = fields.Char(string='Tag 11', related='source_id.tag_11', readonly=True, store=False)
    tag_12 = fields.Char(string='Tag 12', related='source_id.tag_12', readonly=True, store=False)
    tag_13 = fields.Char(string='Tag 13', related='source_id.tag_13', readonly=True, store=False)
    tag_14 = fields.Char(string='Tag 14', related='source_id.tag_14', readonly=True, store=False)
    tag_15 = fields.Char(string='Tag 15', related='source_id.tag_15', readonly=True, store=False)
    tag_16 = fields.Char(string='Tag 16', related='source_id.tag_16', readonly=True, store=False)
    tag_17 = fields.Char(string='Tag 17', related='source_id.tag_17', readonly=True, store=False)
    tag_18 = fields.Char(string='Tag 18', related='source_id.tag_18', readonly=True, store=False)
    tag_19 = fields.Char(string='Tag 19', related='source_id.tag_19', readonly=True, store=False)
    tag_20 = fields.Char(string='Tag 20', related='source_id.tag_20', readonly=True, store=False)
    tag_21 = fields.Char(string='Tag 21', related='source_id.tag_21', readonly=True, store=False)
    tag_22 = fields.Char(string='Tag 22', related='source_id.tag_22', readonly=True, store=False)
    tag_23 = fields.Char(string='Tag 23', related='source_id.tag_23', readonly=True, store=False)
    tag_24 = fields.Char(string='Tag 24', related='source_id.tag_24', readonly=True, store=False)
    tag_25 = fields.Char(string='Tag 25', related='source_id.tag_25', readonly=True, store=False)

    col_01 = fields.Char(string='Col 01')
    col_02 = fields.Char(string='Col 02')
    col_03 = fields.Char(string='Col 03')
    col_04 = fields.Char(string='Col 04')
    col_05 = fields.Char(string='Col 05')
    col_06 = fields.Char(string='Col 06')
    col_07 = fields.Char(string='Col 07')
    col_08 = fields.Char(string='Col 08')
    col_09 = fields.Char(string='Col 09')
    col_10 = fields.Char(string='Col 10')
    col_11 = fields.Char(string='Col 11')
    col_12 = fields.Char(string='Col 12')
    col_13 = fields.Char(string='Col 13')
    col_14 = fields.Char(string='Col 14')
    col_15 = fields.Char(string='Col 15')
    col_16 = fields.Char(string='Col 16')
    col_17 = fields.Char(string='Col 17')
    col_18 = fields.Char(string='Col 18')
    col_19 = fields.Char(string='Col 19')
    col_20 = fields.Char(string='Col 20')
    col_21 = fields.Char(string='Col 21')
    col_22 = fields.Char(string='Col 22')
    col_23 = fields.Char(string='Col 23')
    col_24 = fields.Char(string='Col 24')
    col_25 = fields.Char(string='Col 25')

    for i in range(1, MAX_SHEET_COLUMNS + 1):
        locals()[f"col_{i:02d}_num"] = fields.Float(string=f"Col {i:02d} (Number)")
        locals()[f"col_{i:02d}_int"] = fields.Integer(string=f"Col {i:02d} (Integer)")
        locals()[f"col_{i:02d}_date"] = fields.Date(string=f"Col {i:02d} (Date)")
        locals()[f"col_{i:02d}_datetime"] = fields.Datetime(string=f"Col {i:02d} (Datetime)")
        locals()[f"col_{i:02d}_bool"] = fields.Boolean(string=f"Col {i:02d} (Boolean)")

    _sql_constraints = [
        ('sheet_row_unique', 'unique(source_id, row_number)', 'Row number must be unique per sheet source.'),
    ]

    def action_sync_source(self):
        sources = self.mapped('source_id')
        if sources:
            sources.action_sync()

