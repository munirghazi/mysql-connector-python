# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Unnimaya C O (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import mysql.connector
import re
import ast
import operator
import json
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import logging
import csv
import io
import base64
from datetime import datetime, timedelta
import dateutil.parser
from .mysdb_date_utils import normalize_date_field

_logger = logging.getLogger(__name__)

class MysdbConnector(models.Model):
    """Model for connecting with MySDB"""
    _name = 'mysdb.connector'
    _description = 'MySDB Connector'

    name = fields.Char(string='Name', help='Name of the record',
                       required=True)
    credential_id = fields.Many2one(
        'mysdb.credential',
        string='Connection',
        domain=[('state', '=', 'connect')],
        help='Choose the MySDB connection',
        required=True
    )
    sql_table = fields.Char(string='MySQL Table Name',
                            help='Name of the table in MySQL database',
                            required=True)
    mysql_columns_json = fields.Text(
        string='MySQL Columns (cached)',
        readonly=True,
        help='Cached list of MySQL table columns used for mapping dropdowns.'
    )
    mysql_column_ids = fields.One2many(
        'mysdb.mysql.column',
        'connection_id',
        string='MySQL Columns',
        readonly=True
    )
    model_id = fields.Many2one('ir.model', string='Odoo Table Name',
                               help='Database table in Odoo to which you have'
                                    ' to map the data',
                               domain=lambda self: [
                                   '|',
                                   ('access_ids.group_id', 'in', self.env.user.groups_id.ids),
                                   ('access_ids.group_id', '=', False),
                               ],
                               required=True, ondelete="cascade")
    sync_ids = fields.One2many('sync.table',
                               'connection_id',
                               string='Field Mapping',
                               help='Select the fields to be mapped')
    filter_query = fields.Char(string='SQL WHERE Filter',
                              help='Add a WHERE clause without the "WHERE" keyword.\n'
                                   'Dates can be written as DD/MM/YYYY and will be auto-converted.\n'
                                   'Examples:\n'
                                   '  status="active" AND year=2025\n'
                                   '  created_at > 31/12/2024\n'
                                   '  created_at > 01/01/2025 AND store_id = "qtra"')
    delete_odoo_records = fields.Boolean(string='Delete Odoo Records on Reset',
                                        help='If checked, resetting will also delete the actual records in Odoo (Orders, Products, etc.)')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        help='Company that owns this connector. Leave empty for shared access.'
    )
    auto_sync = fields.Boolean(string='Auto Sync', default=False,
                              help='If enabled, this connector will be synced automatically by the system scheduler.')
    sync_in_progress = fields.Boolean(string='Sync In Progress', default=False,
                                      help='Prevents overlapping sync runs')
    sync_started_at = fields.Datetime(string='Sync Started At', readonly=True)
    is_fetched = fields.Boolean(string='Is Fetched',
                                help='True if once data fetched from mysdb')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('fetched', 'Fetched'),
        ('sync', 'Synced')
    ], string='Status', readonly=True, copy=False, default='draft', help="State of the record")
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    last_sync_message = fields.Text(string='Last Sync Message', readonly=True)

    def _parse_mysql_date(self, date_str, field_type='datetime'):
        """Parse a MySQL date/datetime string using the shared normalizer.
        Kept as a thin wrapper for backward-compatibility with callers."""
        return normalize_date_field(date_str, field_type)

    def _eval_formula(self, expr, row):
        def _coerce(val):
            if val in (None, False, ''):
                return 0
            if isinstance(val, (int, float)):
                return val
            if isinstance(val, bool):
                return int(val)
            try:
                return float(str(val).strip())
            except Exception:
                raise ValidationError(f"Invalid numeric value '{val}' in formula '{expr}'.")

        def _eval(node):
            if isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                op_map = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Mod: operator.mod,
                }
                op_type = type(node.op)
                if op_type not in op_map:
                    raise ValidationError(f"Unsupported operator in formula '{expr}'.")
                return op_map[op_type](left, right)
            if isinstance(node, ast.UnaryOp):
                operand = _eval(node.operand)
                if isinstance(node.op, ast.USub):
                    return -operand
                if isinstance(node.op, ast.UAdd):
                    return +operand
                raise ValidationError(f"Unsupported unary operator in formula '{expr}'.")
            if isinstance(node, ast.Name):
                col_name = node.id
                if col_name not in row:
                    # Try case-insensitive match
                    match = next((k for k in row if k.lower() == col_name.lower()), None)
                    if match:
                        return _coerce(row[match])
                    _logger.warning(
                        "Formula '%s': column '%s' not found in MySQL row. "
                        "Available columns: %s", expr, col_name, list(row.keys())
                    )
                return _coerce(row.get(col_name))
            if isinstance(node, ast.Call):
                # Support safe built-in functions: round, abs, min, max, int, float
                allowed_funcs = {
                    'round': round,
                    'abs': abs,
                    'min': min,
                    'max': max,
                    'int': int,
                    'float': float,
                }
                if isinstance(node.func, ast.Name) and node.func.id in allowed_funcs:
                    args = [_eval(a) for a in node.args]
                    return allowed_funcs[node.func.id](*args)
                func_name = node.func.id if isinstance(node.func, ast.Name) else '?'
                raise ValidationError(f"Unsupported function '{func_name}' in formula '{expr}'.")
            if isinstance(node, ast.IfExp):
                # Ternary: value_if_true if condition else value_if_false
                test_val = _eval(node.test)
                return _eval(node.body) if test_val else _eval(node.orelse)
            if isinstance(node, ast.Compare):
                # Comparisons: amount > 100, tax == 0, price <= 50, etc.
                left = _eval(node.left)
                cmp_ops = {
                    ast.Eq: operator.eq,
                    ast.NotEq: operator.ne,
                    ast.Lt: operator.lt,
                    ast.LtE: operator.le,
                    ast.Gt: operator.gt,
                    ast.GtE: operator.ge,
                }
                # Support chained comparisons: a < b < c
                result = True
                current = left
                for op_node, comparator in zip(node.ops, node.comparators):
                    op_type = type(op_node)
                    if op_type not in cmp_ops:
                        raise ValidationError(f"Unsupported comparison in formula '{expr}'.")
                    right = _eval(comparator)
                    result = result and cmp_ops[op_type](current, right)
                    current = right
                return result
            if isinstance(node, ast.BoolOp):
                # and / or
                if isinstance(node.op, ast.And):
                    return all(_eval(v) for v in node.values)
                if isinstance(node.op, ast.Or):
                    return any(_eval(v) for v in node.values)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                return not _eval(node.operand)
            if isinstance(node, ast.Constant):
                return _coerce(node.value)
            if isinstance(node, ast.Num):
                return _coerce(node.n)
            raise ValidationError(f"Unsupported expression in formula '{expr}'.")

        try:
            tree = ast.parse(expr, mode='eval')
            return _eval(tree.body)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(f"Invalid formula '{expr}': {exc}")

    def _validate_table_name(self, table_name):
        if not table_name or not isinstance(table_name, str):
            raise ValidationError("MySDB table name is required.")
        if not re.match(r'^[A-Za-z0-9_]+$', table_name):
            raise ValidationError("Invalid MySDB table name. Use only letters, numbers, and underscores.")

    def _validate_column_name(self, column_name):
        """Validate that a column name from MySQL only contains safe characters."""
        if not column_name or not isinstance(column_name, str):
            raise ValidationError("Column name is required.")
        if not re.match(r'^[A-Za-z0-9_]+$', column_name):
            raise ValidationError(
                f"Invalid column name '{column_name}'. "
                "Only letters, numbers, and underscores are allowed."
            )

    def _verify_table_exists(self, cursor, table_name):
        """Verify that a table actually exists in the MySQL database via INFORMATION_SCHEMA.
        This prevents any injection through crafted table names."""
        cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (self.credential_id.name, table_name)
        )
        result = cursor.fetchone()
        if not result:
            raise ValidationError(
                f"Table '{table_name}' does not exist in database "
                f"'{self.credential_id.name}'."
            )

    def _normalize_filter_query(self, filter_query):
        if not filter_query:
            return ''
        normalized = str(filter_query).strip()
        normalized = re.sub(r'^\s*where\s+', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'^\s*and\s+', '', normalized, flags=re.IGNORECASE)
        # Auto-convert bare dates DD/MM/YYYY or DD-MM-YYYY to MySQL-quoted 'YYYY-MM-DD'
        # This prevents MySQL from interpreting e.g. 31/12/2024 as division (31÷12÷2024 ≈ 0)
        def _fix_bare_date(m):
            day, sep, month, _, year = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            return f"'{year}-{month.zfill(2)}-{day.zfill(2)}'"
        normalized = re.sub(
            r'(?<![\'"\w])(\d{1,2})([/\-])(\d{1,2})(\2)(\d{4})(?![\'"\w])',
            _fix_bare_date, normalized
        )
        return normalized.strip()

    def _validate_filter_query(self, filter_query):
        if not filter_query:
            return
        # Block comment and statement terminators
        blocked_tokens = [';', '--', '/*', '*/', '@@']
        if any(token in filter_query for token in blocked_tokens):
            raise ValidationError(
                "Invalid SQL filter. Remove comments, statement terminators, "
                "or system variable references (@@)."
            )
        # Block dangerous SQL keywords (case-insensitive, word-boundary match)
        blocked_keywords = [
            r'\bUNION\b', r'\bINTO\b', r'\bOUTFILE\b', r'\bDUMPFILE\b',
            r'\bLOAD_FILE\b', r'\bBENCHMARK\b', r'\bSLEEP\b',
            r'\bDROP\b', r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b',
            r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bGRANT\b',
            r'\bEXEC\b', r'\bEXECUTE\b', r'\bCALL\b',
        ]
        for pattern in blocked_keywords:
            if re.search(pattern, filter_query, flags=re.IGNORECASE):
                keyword = re.search(pattern, filter_query, flags=re.IGNORECASE).group()
                raise ValidationError(
                    f"Invalid SQL filter: '{keyword}' is not allowed in filter queries. "
                    "Only WHERE-style conditions are permitted "
                    "(e.g. status='active' AND year=2025)."
                )
        # Block subqueries — no parenthesised SELECT allowed
        if re.search(r'\(\s*SELECT\b', filter_query, flags=re.IGNORECASE):
            raise ValidationError(
                "Invalid SQL filter: sub-queries are not allowed. "
                "Only simple WHERE conditions are permitted."
            )

    @api.onchange('model_id', 'sql_table')
    def _onchange_model_id(self):
        """Method for reloading the one2many field only when critical values change"""
        if self._origin.model_id != self.model_id or self._origin.sql_table != self.sql_table:
            # Only reset if the table or model has actually changed in the UI
            self.is_fetched = False

    def action_sync_table(self):
        """Method for syncing tables with true batch streaming for very large datasets"""
        if not self.sync_ids:
            raise ValidationError("Please map the fields before syncing.")
        if self.sync_in_progress:
            # Auto-clear stale lock after 30 minutes (network drop / crash)
            if self.sync_started_at and fields.Datetime.now() > (self.sync_started_at + timedelta(minutes=30)):
                self.write({'sync_in_progress': False, 'sync_started_at': False})
            else:
                raise ValidationError("A sync is already in progress for this connector.")
        self._validate_table_name(self.sql_table)
        filter_query = self._normalize_filter_query(self.filter_query)
        self._validate_filter_query(filter_query)
        if filter_query:
            _logger.info("Sync %s: normalized SQL filter → %s", self.sql_table, filter_query)

        # 1. Connection and Schema
        connect_kwargs = self.credential_id._build_connect_kwargs()
        connection = mysql.connector.connect(**connect_kwargs)
        cursor = connection.cursor(dictionary=True)
        
        try:
            self.write({'sync_in_progress': True, 'sync_started_at': fields.Datetime.now()})

            # Verify the table actually exists in the database (prevents injection)
            self._verify_table_exists(cursor, self.sql_table)

            cursor.execute(
                "SELECT COLUMN_NAME, COLUMN_KEY FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (self.credential_id.name, self.sql_table)
            )
            field_list = cursor.fetchall()
            unique = next(
                (rec['COLUMN_NAME'] for rec in field_list if rec.get('COLUMN_KEY', '').upper() == 'PRI'),
                next((rec['COLUMN_NAME'] for rec in field_list if rec.get('COLUMN_KEY', '').upper() == 'UNI'), None)
            )
            
            if not unique:
                raise ValidationError(f"Table {self.sql_table} needs a Unique/Primary key.")
            # Validate that the unique column name is safe for SQL interpolation
            self._validate_column_name(unique)

            model_obj = self.env[self.model_id.model]

            # 1b. Backfill old imported.data entries that have no connection_id.
            #     ONLY safe when this is the sole connector for this model+table.
            #     If multiple connectors share the same model+table, skip backfill
            #     to avoid wrongly assigning records across stores.
            orphan_count = self.env['imported.data'].sudo().search_count([
                ('connection_id', '=', False),
                ('model_id', '=', self.model_id.id),
                ('mysdb_table', '=', self.sql_table),
            ])
            if orphan_count:
                sibling_connectors = self.search_count([
                    ('model_id', '=', self.model_id.id),
                    ('sql_table', '=', self.sql_table),
                ])
                if sibling_connectors <= 1:
                    _logger.info(
                        "Sync %s: backfilling %d imported.data entries with connection_id=%d (sole connector)",
                        self.sql_table, orphan_count, self.id
                    )
                    self.env['imported.data'].sudo().search([
                        ('connection_id', '=', False),
                        ('model_id', '=', self.model_id.id),
                        ('mysdb_table', '=', self.sql_table),
                    ]).write({'connection_id': self.id})
                else:
                    _logger.warning(
                        "Sync %s: %d orphan imported.data entries found but %d connectors share "
                        "this model+table. Skipping backfill — delete orphan entries manually or "
                        "clear and re-sync both connectors.",
                        self.sql_table, orphan_count, sibling_connectors
                    )

            # 2. Get Total Count for progress tracking
            # table name is validated (alphanumeric+underscore) and verified to exist
            safe_table = self.sql_table
            where_clause = f" WHERE {filter_query}" if filter_query else ""
            cursor.execute(f"SELECT COUNT(*) as total FROM `{safe_table}`{where_clause};")
            total_records = cursor.fetchone()['total']
            _logger.info(f"Starting sync for {safe_table}: {total_records} records found.")

            batch_size = 1000
            last_seen = None
            processed = 0
            total_created = 0
            mysql_columns = []
            debug_formula_info = ""
            total_updated = 0
            total_skipped = 0
            batch_errors = []

            # Detect required fields on the target model once (skip relational ones
            # which are often handled via FK mapping and may legitimately be absent).
            model_fields_meta = model_obj.fields_get()
            required_char_fields = {
                fname for fname, fmeta in model_fields_meta.items()
                if fmeta.get('required') and fmeta.get('type') in ('char', 'integer', 'float', 'text')
            }
            # Only check required fields that are actually in our mapping
            mapped_fields = {rec.ir_field_id.name for rec in self.sync_ids if rec.ir_field_id}
            required_char_fields = required_char_fields & mapped_fields
            if required_char_fields:
                _logger.info("Sync %s: required fields that will be validated: %s", safe_table, required_char_fields)

            while True:
                # 3. Fetch MySQL Batch using keyset pagination
                keyset_where = where_clause
                params = []
                if last_seen is not None:
                    keyset_where = f"{where_clause} AND `{unique}` > %s" if where_clause else f" WHERE `{unique}` > %s"
                    params.append(last_seen)
                cursor.execute(
                    f"SELECT * FROM `{safe_table}`{keyset_where} ORDER BY `{unique}` ASC LIMIT {batch_size};",
                    params
                )
                records = cursor.fetchall()
                if not records:
                    break

                # Log MySQL column names and first record (first batch only) for debugging
                if processed == 0 and records:
                    mysql_columns = list(records[0].keys())
                    _logger.info("Sync %s: MySQL columns = %s", safe_table, mysql_columns)
                    # Log first record sample to help debug mapping issues
                    sample = {k: str(v)[:50] if v is not None else 'NULL' for k, v in records[0].items()}
                    _logger.info("Sync %s: first record sample = %s", safe_table, sample)

                # 4. Pre-fetch existing synced records for THIS BATCH + THIS CONNECTOR
                batch_mysql_refs = [str(item[unique]) for item in records]
                existing_imported = self.env['imported.data'].sudo().search_read([
                    ('connection_id', '=', self.id),
                    ('model_id', '=', self.model_id.id),
                    ('mysdb_table', '=', self.sql_table),
                    ('mysdb_ref', 'in', batch_mysql_refs)
                ], ['mysdb_ref', 'odoo_ref'])
                synced_map = {rec['mysdb_ref']: rec['odoo_ref'] for rec in existing_imported}

                # 4b. Verify that the referenced Odoo records still exist
                #     (they may have been deleted manually or by a previous rollback)
                if synced_map:
                    existing_ids = set(model_obj.browse(list(synced_map.values())).exists().ids)
                    stale_refs = [ref for ref, oid in synced_map.items() if oid not in existing_ids]
                    if stale_refs:
                        _logger.warning(
                            "Sync %s: %d stale import-log entries (Odoo records deleted). Will re-create.",
                            safe_table, len(stale_refs)
                        )
                        # Remove stale imported.data so the records are treated as new
                        self.env['imported.data'].sudo().search([
                            ('connection_id', '=', self.id),
                            ('model_id', '=', self.model_id.id),
                            ('mysdb_table', '=', self.sql_table),
                            ('mysdb_ref', 'in', stale_refs)
                        ]).unlink()
                        for ref in stale_refs:
                            del synced_map[ref]

                # 5. Pre-fetch Foreign Key mappings for THIS BATCH ONLY
                #    Scope by connection_id so we only use FK refs from this connector,
                #    and also accept orphan entries (connection_id=False) as fallback.
                fk_mappings = {}
                for sync_rec in self.sync_ids.filtered(lambda r: r.foreign_key):
                    fk_vals = list(set(str(item[sync_rec.mysql_field]) for item in records if item.get(sync_rec.mysql_field)))
                    if fk_vals:
                        found_fks = self.env['imported.data'].sudo().search_read([
                            '|',
                            ('connection_id', '=', self.id),
                            ('connection_id', '=', False),
                            ('mysdb_table', '=', sync_rec.ref_table),
                            ('mysdb_ref', 'in', fk_vals)
                        ], ['mysdb_ref', 'odoo_ref'])
                        if sync_rec.ref_table not in fk_mappings:
                            fk_mappings[sync_rec.ref_table] = {}
                        for f in found_fks:
                            fk_mappings[sync_rec.ref_table][f['mysdb_ref']] = f['odoo_ref']

                # 5b. Remove stale FK refs (pointing to deleted Odoo records)
                #     Records with missing FK targets are still created — just without the link.
                #     Use the Data Maintenance Audit to find and fix missing references later.
                for table_name, ref_map in fk_mappings.items():
                    if not ref_map:
                        continue
                    odoo_ids = list(set(ref_map.values()))
                    fk_sync = self.sync_ids.filtered(
                        lambda r: r.foreign_key and r.ref_table == table_name
                    )
                    if fk_sync and fk_sync[0].ir_field_id and fk_sync[0].ir_field_id.relation:
                        fk_model = self.env[fk_sync[0].ir_field_id.relation]
                        existing_fk_ids = set(fk_model.browse(odoo_ids).exists().ids)
                        stale_fk = [k for k, v in ref_map.items() if v not in existing_fk_ids]
                        if stale_fk:
                            _logger.info(
                                "Sync %s: %d FK refs for '%s' point to deleted records — "
                                "order details will be created without the link. "
                                "Use Data Maintenance Audit to review.",
                                safe_table, len(stale_fk), table_name
                            )
                            for k in stale_fk:
                                del ref_map[k]

                # 6. Process Batch
                records_to_create = []
                import_log_refs = []
                skipped_empty = 0
                skipped_required = 0
                updated_count = 0

                # Pre-collect fields that have formula/constant overrides
                # so regular mysql mappings don't overwrite them
                priority_fields = set()
                for rec in self.sync_ids:
                    if rec.ir_field_id:
                        mode = rec.mapping_mode or (
                            'constant' if rec.use_constant else (
                                'formula' if rec.use_formula else 'mysql'
                            )
                        )
                        if mode in ('formula', 'constant'):
                            priority_fields.add(rec.ir_field_id.name)

                # Debug: log priority fields once
                if processed == 0 and priority_fields:
                    _logger.info("Sync %s: priority_fields (formula/constant) = %s", safe_table, priority_fields)
                    for rec in self.sync_ids:
                        if rec.ir_field_id:
                            _logger.info(
                                "  mapping: %s -> %s (mode=%s, formula=%s, use_const=%s, use_formula=%s)",
                                rec.ir_field_id.name, rec.mysql_field_id.name if rec.mysql_field_id else rec.mysql_field,
                                rec.mapping_mode, rec.formula_expression, rec.use_constant, rec.use_formula
                            )

                for item in records:
                    ref_val = str(item[unique])
                    odoo_id = synced_map.get(ref_val)
                    
                    vals = {}
                    debug_first = (processed == 0 and ref_val == str(records[0][unique]))
                    for rec in self.sync_ids:
                        if not rec.ir_field_id: continue
                        # Backward-compat: fall back to legacy boolean fields if mapping_mode is unset
                        mapping_mode = rec.mapping_mode or (
                            'constant' if rec.use_constant else (
                                'formula' if rec.use_formula else 'mysql'
                            )
                        )

                        # Skip regular mysql mapping if a formula/constant exists for same field
                        if mapping_mode == 'mysql' and rec.ir_field_id.name in priority_fields:
                            if debug_first:
                                _logger.info("  SKIPPED mysql mapping for '%s' (formula takes priority)", rec.ir_field_id.name)
                            continue

                        if mapping_mode == 'constant':
                            mysql_val = rec.constant_value
                        elif mapping_mode == 'formula':
                            mysql_val = self._eval_formula(rec.formula_expression, item)
                            if debug_first:
                                _logger.info("  FORMULA '%s' = %s (expr: %s)", rec.ir_field_id.name, mysql_val, rec.formula_expression)
                                debug_formula_info = f"Formula '{rec.formula_expression}' -> {mysql_val}"
                        else:
                            field_name = rec.mysql_field_id.name if rec.mysql_field_id else rec.mysql_field
                            mysql_val = item.get(field_name)
                        if mysql_val is None: continue

                        if mapping_mode in ('constant', 'formula') or not rec.foreign_key:
                            # Parse dates if Odoo field is Datetime/Date
                            if rec.ir_field_id.ttype in ['datetime', 'date']:
                                vals[rec.ir_field_id.name] = self._parse_mysql_date(mysql_val, rec.ir_field_id.ttype)
                            # Clean IDs and Codes
                            elif isinstance(mysql_val, str) and rec.ir_field_id.name in ['order_id', 'order_linked_id', 'order_code']:
                                vals[rec.ir_field_id.name] = mysql_val.strip()
                            else:
                                vals[rec.ir_field_id.name] = mysql_val
                        else:
                            # Map FK — stale refs already removed in step 5b
                            odoo_ref = fk_mappings.get(rec.ref_table, {}).get(str(mysql_val))
                            if odoo_ref:
                                vals[rec.ir_field_id.name] = odoo_ref

                    if not vals:
                        skipped_empty += 1
                        continue

                    if odoo_id:
                        # Update existing — verify record still exists first
                        existing_rec = model_obj.browse(odoo_id).exists()
                        if existing_rec:
                            try:
                                with self.env.cr.savepoint():
                                    existing_rec.write(vals)
                                updated_count += 1
                            except Exception as upd_err:
                                if not batch_errors or len(batch_errors) < 5:
                                    batch_errors.append(
                                        f"Update {ref_val} failed: {str(upd_err)[:150]}"
                                    )
                                _logger.warning(
                                    "Sync %s: update record %s (id=%d) failed: %s",
                                    safe_table, ref_val, odoo_id, upd_err
                                )
                        else:
                            # Record deleted between stale check and now — treat as new
                            _logger.warning(
                                "Sync %s: record %s (id=%d) deleted mid-sync. Re-creating.",
                                safe_table, ref_val, odoo_id
                            )
                            # Remove the stale imported.data entry
                            self.env['imported.data'].sudo().search([
                                ('connection_id', '=', self.id),
                                ('model_id', '=', self.model_id.id),
                                ('mysdb_table', '=', self.sql_table),
                                ('mysdb_ref', '=', ref_val)
                            ]).unlink()
                            records_to_create.append(vals)
                            import_log_refs.append(ref_val)
                    else:
                        # Check required fields before queuing for creation
                        missing = [f for f in required_char_fields if not vals.get(f)]
                        if missing:
                            skipped_required += 1
                            if skipped_required <= 3:  # Log first few for debugging
                                _logger.warning(
                                    "Sync %s: skipping record ref=%s — missing required field(s): %s",
                                    safe_table, ref_val, missing
                                )
                            continue
                        # Queue for creation
                        records_to_create.append(vals)
                        import_log_refs.append(ref_val)

                # 7. Create and Log Batch (inside savepoint to avoid killing the whole transaction)
                batch_created = 0
                if records_to_create:
                    try:
                        with self.env.cr.savepoint():
                            new_recs = model_obj.create(records_to_create)
                            log_vals = [{
                                'connection_id': self.id,
                                'model_id': self.model_id.id,
                                'mysdb_ref': import_log_refs[j],
                                'mysdb_table': self.sql_table,
                                'odoo_ref': new_recs[j].id,
                                'log_note': 'Success'
                            } for j in range(len(new_recs))]
                            self.env['imported.data'].sudo().create(log_vals)
                            batch_created = len(new_recs)
                    except Exception as batch_err:
                        # Batch failed — fall back to one-by-one to salvage valid records
                        # Identify ALL Many2one fields on the model (not just FK-mapped ones)
                        # so we can strip them on retry if a FK constraint fails
                        m2o_fields = {
                            fname for fname, finfo in model_fields_meta.items()
                            if finfo.get('type') == 'many2one'
                        }
                        _logger.warning(
                            "Sync %s: batch create failed, falling back to one-by-one (%d records): %s",
                            safe_table, len(records_to_create), batch_err
                        )
                        for idx, single_vals in enumerate(records_to_create):
                            try:
                                with self.env.cr.savepoint():
                                    new_rec = model_obj.create([single_vals])
                                    self.env['imported.data'].sudo().create({
                                        'connection_id': self.id,
                                        'model_id': self.model_id.id,
                                        'mysdb_ref': import_log_refs[idx],
                                        'mysdb_table': self.sql_table,
                                        'odoo_ref': new_rec.id,
                                        'log_note': 'Success (fallback)'
                                    })
                                    batch_created += 1
                            except Exception:
                                # Retry without ALL Many2one fields (e.g. product_ref_id)
                                retry_vals = {k: v for k, v in single_vals.items() if k not in m2o_fields}
                                if retry_vals != single_vals:
                                    try:
                                        with self.env.cr.savepoint():
                                            new_rec = model_obj.create([retry_vals])
                                            self.env['imported.data'].sudo().create({
                                                'connection_id': self.id,
                                                'model_id': self.model_id.id,
                                                'mysdb_ref': import_log_refs[idx],
                                                'mysdb_table': self.sql_table,
                                                'odoo_ref': new_rec.id,
                                                'log_note': 'Success (no FK link)'
                                            })
                                            batch_created += 1
                                            continue
                                    except Exception as retry_err:
                                        _logger.warning(
                                            "Sync %s: record %s failed even without FK: %s",
                                            safe_table, import_log_refs[idx], retry_err
                                        )
                                if not batch_errors:
                                    batch_errors.append(
                                        f"Record {import_log_refs[idx]} failed: {batch_err}"
                                    )
                        if len(records_to_create) > batch_created:
                            failed_count = len(records_to_create) - batch_created
                            _logger.warning(
                                "Sync %s: one-by-one fallback: %d succeeded, %d failed",
                                safe_table, batch_created, failed_count
                            )

                # 8. Increment progress
                total_created += batch_created
                total_updated += updated_count
                total_skipped += skipped_empty + skipped_required
                processed += len(records)
                last_seen = records[-1][unique]
                _logger.info(
                    "Sync %s batch: fetched=%d, already_synced=%d, updated=%d, "
                    "created=%d, skipped_empty=%d, skipped_required=%d, progress=%d/%d, last_key=%s",
                    safe_table, len(records), len(synced_map),
                    updated_count, batch_created,
                    skipped_empty, skipped_required, processed, total_records, last_seen
                )

            sync_msg = (
                f"MySQL total: {total_records} | "
                f"Created: {total_created} | Updated: {total_updated} | "
                f"Skipped: {total_skipped}"
            )
            if batch_errors:
                sync_msg += f" | ERRORS ({len(batch_errors)}): {batch_errors[0][:200]}"
            if debug_formula_info:
                sync_msg += f" | {debug_formula_info}"
            if mysql_columns:
                sync_msg += f" | Columns: {mysql_columns}"
            self.write({
                'state': 'sync',
                'last_sync_date': fields.Datetime.now(),
                'last_sync_message': sync_msg
            })
            self.env['mysdb.sync.log'].sudo().create({
                'source_type': 'connector',
                'source_name': self.name,
                'sync_datetime': fields.Datetime.now(),
                'sync_status': 'ok',
                'sync_message': sync_msg,
            })
            
        except Exception as e:
            _logger.error("Sync %s failed: %s", self.sql_table, e)
            try:
                with self.env.cr.savepoint():
                    self.write({
                        'last_sync_message': f"Error during sync: {str(e)}"
                    })
                    self.env['mysdb.sync.log'].sudo().create({
                        'source_type': 'connector',
                        'source_name': self.name,
                        'sync_datetime': fields.Datetime.now(),
                        'sync_status': 'error',
                        'sync_message': f"Error during sync: {str(e)}"[:500],
                    })
            except Exception:
                _logger.error("Sync %s: could not write error log to DB (transaction aborted)", self.sql_table)
            raise ValidationError(f"Sync failed: {str(e)}")
        finally:
            try:
                with self.env.cr.savepoint():
                    self.write({'sync_in_progress': False, 'sync_started_at': False})
            except Exception:
                _logger.error("Sync %s: could not clear sync lock (transaction aborted)", self.sql_table)
            cursor.close()
            connection.close()

    def action_clear_sync_lock(self):
        """Manually clear a stuck sync lock (e.g., after a crash)."""
        self.write({'sync_in_progress': False, 'sync_started_at': False})
        return True

    def action_clear_imported_data(self):
        """Delete all imported.data entries for this connector, allowing a fresh re-sync.
        Does NOT delete the actual Odoo records — only the sync tracking log."""
        self.ensure_one()
        deleted = self.env['imported.data'].sudo().search([
            ('connection_id', '=', self.id),
            ('model_id', '=', self.model_id.id),
            ('mysdb_table', '=', self.sql_table),
        ])
        count = len(deleted)
        deleted.unlink()
        # Also clean orphan entries (no connection_id) for this model+table
        orphans = self.env['imported.data'].sudo().search([
            ('connection_id', '=', False),
            ('model_id', '=', self.model_id.id),
            ('mysdb_table', '=', self.sql_table),
        ])
        orphan_count = len(orphans)
        orphans.unlink()
        msg = f"Cleared {count} sync log entries + {orphan_count} orphan entries for {self.sql_table}."
        _logger.info(msg)
        self.write({'last_sync_message': msg})
        return True

    def action_download_csv(self):
        """Generates and downloads a CSV of the synced data in Odoo.
        Only exports records that were synced by THIS connector (via imported.data log)."""
        self.ensure_one()
        model_name = self.model_id.model
        # Use search_read for better memory performance with 200k records
        fields_to_export = [f.name for f in self.sync_ids.ir_field_id]
        if not fields_to_export:
            raise ValidationError("No fields mapped for export.")

        # Scope to records imported for this table/model/connector
        synced_logs = self.env['imported.data'].sudo().search_read([
            ('connection_id', '=', self.id),
            ('model_id', '=', self.model_id.id),
            ('mysdb_table', '=', self.sql_table),
        ], ['odoo_ref'])
        odoo_ids = [log['odoo_ref'] for log in synced_logs if log.get('odoo_ref')]

        if not odoo_ids:
            raise ValidationError("No synced data found for this connector. Sync first before exporting.")

        records = self.env[model_name].search_read(
            [('id', 'in', odoo_ids)], fields_to_export
        )
        
        if not records:
            raise ValidationError("No data found to export.")

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # Header
        writer.writerow(fields_to_export)
        
        # Data
        for rec in records:
            row = [rec.get(f) for f in fields_to_export]
            writer.writerow(row)
            
        data = output.getvalue().encode('utf-8')
        output.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.sql_table}_export.csv',
            'type': 'binary',
            'datas': base64.b64encode(data),
            'mimetype': 'text/csv',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_clean_data(self):
        """Method to strip whitespace from existing data to fix join issues"""
        model_name = self.model_id.model
        model_obj = self.env[model_name].sudo()
        
        # Identify fields that need cleaning
        fields_to_clean = [f for f in ['order_id', 'order_linked_id', 'order_code'] if f in model_obj._fields]
        
        if not fields_to_clean:
            return

        # Process in batches to avoid timeout
        records = model_obj.search([])
        count = 0
        for rec in records:
            vals = {}
            for field in fields_to_clean:
                val = getattr(rec, field)
                if isinstance(val, str) and val != val.strip():
                    vals[field] = val.strip()
            
            if vals:
                rec.write(vals)
                count += 1
            
            # Flush ORM cache periodically to keep memory usage bounded
            if count > 0 and count % 1000 == 0:
                self.env.cr.flush()
                self.env.invalidate_all()
                
        _logger.info(f"Cleaned whitespace for {count} records in {model_name}")

        self.write({'state': 'sync'})

    def action_reset_connector(self):
        """Method to reset the sync logs and optionally the Odoo records"""
        self.ensure_one()
        
        # 1. Delete Sync Logs
        logs = self.env['imported.data'].sudo().search([
            ('connection_id', '=', self.id),
            ('model_id', '=', self.model_id.id),
            ('mysdb_table', '=', self.sql_table)
        ])
        
        # 2. Optionally Delete Odoo Records
        if self.delete_odoo_records:
            odoo_ids = logs.mapped('odoo_ref')
            if odoo_ids:
                model_obj = self.env[self.model_id.model].sudo()
                records = model_obj.browse(odoo_ids).exists()
                if records:
                    records.unlink()
        
        # 3. Delete Logs after records (to maintain FKs if any)
        logs.unlink()
        
        # 4. Reset State
        self.write({
            'state': 'fetched',
            'last_sync_date': False,
            'last_sync_message': f"Connector reset successful. Logs cleared. Odoo records deleted: {self.delete_odoo_records}"
        })
        return True

    @api.model
    def cron_auto_sync_all(self):
        """Method called by scheduled action to sync all connectors with auto_sync=True"""
        connectors = self.search([
            ('auto_sync', '=', True),
            ('state', 'in', ['fetched', 'sync']),
            ('sync_in_progress', '=', False),
        ])
        for conn in connectors:
            try:
                conn.action_sync_table()
                _logger.info(f"Auto-sync completed for connector: {conn.name}")
            except Exception as e:
                _logger.error(f"Auto-sync failed for connector {conn.name}: {str(e)}")

    def action_fetch_data(self):
        """Method for fetching the columns of MySDB table while preserving existing mappings"""
        self._validate_table_name(self.sql_table)
        # Use INFORMATION_SCHEMA to safely list columns (parameterized, no injection)
        records = self.mysql_connect(
            "SELECT COLUMN_NAME as `Field`, COLUMN_KEY as `Key` "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            params=(self.credential_id.name, self.sql_table)
        )
        mysql_columns = [rec.get('Field') for rec in records if rec.get('Field')]
        self.write({'mysql_columns_json': json.dumps(mysql_columns)})
        self.mysql_column_ids.unlink()
        if mysql_columns:
            self.write({
                'mysql_column_ids': [(0, 0, {'name': col}) for col in mysql_columns]
            })
        if not any(key in rec.get('Key', '') for rec in records for
                   key in ['PRI', 'UNI']):
            raise ValidationError(
                "The MySDB table cannot be imported because it "
                "doesn't have a Unique or Primary key.")
        
        existing_fields = self.sync_ids.mapped('ir_field_id')
        sync_vals = []
        
        if records and self.model_id:
            model_fields = self.env['ir.model.fields'].search([
                ('model_id', '=', self.model_id.id),
                ('store', '=', True),
            ], order='name asc')
            for field in model_fields:
                if field in existing_fields:
                    continue
                vals = {
                    'connection_id': self.id,
                    'data_type': field.ttype,
                    'model_id': self.model_id.id,
                    'ir_field_id': field.id,
                    'mapping_mode': 'mysql',
                }
                sync_vals.append((0, 0, vals))
            
            if sync_vals:
                self.write({'sync_ids': sync_vals})
            
            self.write({
                'state': 'fetched',
                'is_fetched': True
            })

    def mysql_connect(self, query, params=None):
        """Method for connecting with MySDB.
        Args:
            query: SQL query string. Use %s placeholders for parameters.
            params: Tuple of parameter values for the query (prevents SQL injection).
        """
        try:
            if not re.match(r'^\s*(SELECT|SHOW|DESCRIBE)\b', query, flags=re.IGNORECASE):
                raise ValidationError("Only SELECT/SHOW/DESCRIBE queries are allowed.")
            connect_kwargs = self.credential_id._build_connect_kwargs()
            connection = mysql.connector.connect(**connect_kwargs)
            if not connection.is_connected():
                raise ValidationError(f"Error connecting to MySDB")
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            self.is_fetched = True
            cursor.close()
            connection.close()
            return results
        except mysql.connector.Error as e:
            raise ValidationError(f"Error connecting to MySDB: {e}")
