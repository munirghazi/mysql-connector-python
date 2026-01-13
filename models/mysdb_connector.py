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
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import logging
import csv
import io
import base64
from datetime import datetime
import dateutil.parser

_logger = logging.getLogger(__name__)

class MysdbConnector(models.Model):
    """Model for connecting with MySDB"""
    _name = 'mysdb.connector'
    _description = 'MySDB Connector'

    name = fields.Char(string='Name', help='Name of the record',
                       required=True)
    credential_id = fields.Many2one('mysdb.credential',
                                    string='Connection', domain="[('state', '=', 'connect')]",
                                    help='Choose the MySDB connection',
                                    required=True)
    sql_table = fields.Char(string='MySDB Table Name',
                            help='Name of the table in MySDB database',
                            required=True)
    model_id = fields.Many2one('ir.model', string='Odoo Table Name',
                               help='Database table in Odoo to which you have'
                                    ' to map the data',
                               domain=lambda self: [(
                                   'access_ids', 'not in',
                                   self.env.user.groups_id.ids)],
                               required=True, ondelete="cascade")
    sync_ids = fields.One2many('sync.table',
                               'connection_id',
                               string='Field Mapping',
                               help='Select the fields to be mapped')
    filter_query = fields.Char(string='SQL Filter',
                              help='Add a WHERE clause without the "WHERE" keyword. Example: status="active" AND year=2025')
    delete_odoo_records = fields.Boolean(string='Delete Odoo Records on Reset',
                                        help='If checked, resetting will also delete the actual records in Odoo (Orders, Products, etc.)')
    auto_sync = fields.Boolean(string='Auto Sync', default=False,
                              help='If enabled, this connector will be synced automatically by the system scheduler.')
    is_fetched = fields.Boolean(string='Is Fetched',
                                help='True if once data fetched from mysdb')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('fetched', 'Fetched'),
        ('sync', 'Synced')
    ], string='Status', readonly=True, copy=False, default='draft', help="State of the record")
    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)
    last_sync_message = fields.Text(string='Last Sync Message', readonly=True)

    def _parse_mysql_date(self, date_str):
        if not date_str or not isinstance(date_str, str):
            return date_str
        
        # Handle Arabic AM/PM formats like "28-05-2025 | 11:58 م"
        clean_date = date_str.replace('م', 'PM').replace('ص', 'AM').replace('|', '').strip()
        
        try:
            # Try parsing with dayfirst=True for DD-MM-YYYY formats
            dt = dateutil.parser.parse(clean_date, dayfirst=True)
            return fields.Datetime.to_string(dt)
        except Exception:
            return date_str

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

        # 1. Connection and Schema
        connection = mysql.connector.connect(
            host=self.credential_id.host,
            user=self.credential_id.user,
            password=self.credential_id._decrypt_password(),
            database=self.credential_id.name
        )
        cursor = connection.cursor(dictionary=True)
        
        try:
            cursor.execute(f"SHOW COLUMNS FROM `{self.sql_table}`;")
            field_list = cursor.fetchall()
            unique = next((rec['Field'] for rec in field_list if rec.get('Key', '').upper() == 'PRI'),
                          next((rec['Field'] for rec in field_list if rec.get('Key', '').upper() == 'UNI'), None))
            
            if not unique:
                raise ValidationError(f"Table {self.sql_table} needs a Unique/Primary key.")

            model_obj = self.env[self.model_id.model]
            
            # 2. Get Total Count for progress tracking
            where_clause = f" WHERE {self.filter_query}" if self.filter_query else ""
            cursor.execute(f"SELECT COUNT(*) as total FROM `{self.sql_table}`{where_clause};")
            total_records = cursor.fetchone()['total']
            _logger.info(f"Starting sync for {self.sql_table}: {total_records} records found.")

            batch_size = 1000
            offset = 0

            while offset < total_records:
                # 3. Fetch MySQL Batch
                cursor.execute(f"SELECT * FROM `{self.sql_table}`{where_clause} LIMIT {batch_size} OFFSET {offset};")
                records = cursor.fetchall()
                if not records:
                    break

                # 4. Pre-fetch existing synced records for THIS BATCH ONLY
                batch_mysql_refs = [str(item[unique]) for item in records]
                existing_imported = self.env['imported.data'].sudo().search_read([
                    ('model_id', '=', self.model_id.id),
                    ('mysdb_table', '=', self.sql_table),
                    ('mysdb_ref', 'in', batch_mysql_refs)
                ], ['mysdb_ref', 'odoo_ref'])
                synced_map = {rec['mysdb_ref']: rec['odoo_ref'] for rec in existing_imported}

                # 5. Pre-fetch Foreign Key mappings for THIS BATCH ONLY
                fk_mappings = {}
                for sync_rec in self.sync_ids.filtered(lambda r: r.foreign_key):
                    fk_vals = list(set(str(item[sync_rec.mysql_field]) for item in records if item.get(sync_rec.mysql_field)))
                    if fk_vals:
                        found_fks = self.env['imported.data'].sudo().search_read([
                            ('mysdb_table', '=', sync_rec.ref_table),
                            ('mysdb_ref', 'in', fk_vals)
                        ], ['mysdb_ref', 'odoo_ref'])
                        if sync_rec.ref_table not in fk_mappings:
                            fk_mappings[sync_rec.ref_table] = {}
                        for f in found_fks:
                            fk_mappings[sync_rec.ref_table][f['mysdb_ref']] = f['odoo_ref']

                # 6. Process Batch
                records_to_create = []
                import_log_refs = []
                
                for item in records:
                    ref_val = str(item[unique])
                    odoo_id = synced_map.get(ref_val)
                    
                    vals = {}
                    for rec in self.sync_ids:
                        if not rec.ir_field_id: continue
                        mysql_val = item.get(rec.mysql_field)
                        if mysql_val is None: continue

                        if not rec.foreign_key:
                            # Parse dates if Odoo field is Datetime/Date
                            if rec.ir_field_id.ttype in ['datetime', 'date']:
                                vals[rec.ir_field_id.name] = self._parse_mysql_date(mysql_val)
                            # Clean IDs and Codes
                            elif isinstance(mysql_val, str) and rec.ir_field_id.name in ['order_id', 'order_linked_id', 'order_code']:
                                vals[rec.ir_field_id.name] = mysql_val.strip()
                            else:
                                vals[rec.ir_field_id.name] = mysql_val
                        else:
                            # Map FK
                            odoo_ref = fk_mappings.get(rec.ref_table, {}).get(str(mysql_val))
                            if odoo_ref:
                                vals[rec.ir_field_id.name] = odoo_ref

                    if not vals: continue

                    if odoo_id:
                        # Update existing
                        model_obj.browse(odoo_id).write(vals)
                    else:
                        # Queue for creation
                        records_to_create.append(vals)
                        import_log_refs.append(ref_val)

                # 7. Create and Log Batch
                if records_to_create:
                    new_recs = model_obj.create(records_to_create)
                    log_vals = [{
                        'model_id': self.model_id.id,
                        'mysdb_ref': import_log_refs[j],
                        'mysdb_table': self.sql_table,
                        'odoo_ref': new_recs[j].id,
                        'log_note': 'Success'
                    } for j in range(len(new_recs))]
                    self.env['imported.data'].sudo().create(log_vals)

                # 8. Increment and Commit
                offset += batch_size
                _logger.info(f"Processed {min(offset, total_records)} / {total_records} records for {self.sql_table}")
                self.env.cr.commit() # Save progress to DB

            self.write({
                'state': 'sync',
                'last_sync_date': fields.Datetime.now(),
                'last_sync_message': f"Successfully synced {total_records} records."
            })
            
        except Exception as e:
            self.write({
                'last_sync_message': f"Error during sync: {str(e)}"
            })
            raise ValidationError(f"Sync failed: {str(e)}")
        finally:
            cursor.close()
            connection.close()

    def action_download_csv(self):
        """Generates and downloads a CSV of the synced data in Odoo"""
        self.ensure_one()
        model_name = self.model_id.model
        # Use search_read for better memory performance with 200k records
        fields_to_export = [f.name for f in self.sync_ids.ir_field_id]
        if not fields_to_export:
            raise ValidationError("No fields mapped for export.")
            
        records = self.env[model_name].search_read([], fields_to_export)
        
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
            
            if count > 0 and count % 1000 == 0:
                self.env.cr.commit()
                
        _logger.info(f"Cleaned whitespace for {count} records in {model_name}")

        self.write({'state': 'sync'})

    def action_reset_connector(self):
        """Method to reset the sync logs and optionally the Odoo records"""
        self.ensure_one()
        
        # 1. Delete Sync Logs
        logs = self.env['imported.data'].sudo().search([
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
        connectors = self.search([('auto_sync', '=', True), ('state', 'in', ['fetched', 'sync'])])
        for conn in connectors:
            try:
                conn.action_sync_table()
                _logger.info(f"Auto-sync completed for connector: {conn.name}")
            except Exception as e:
                _logger.error(f"Auto-sync failed for connector {conn.name}: {str(e)}")

    def action_fetch_data(self):
        """Method for fetching the columns of MySDB table while preserving existing mappings"""
        records = self.mysql_connect(f"SHOW COLUMNS FROM `{self.sql_table}`;")
        if not any(key in rec.get('Key', '') for rec in records for
                   key in ['PRI', 'UNI']):
            raise ValidationError(
                "The MySDB table cannot be imported because it "
                "doesn't have a Unique or Primary key.")
        
        existing_fields = self.sync_ids.mapped('mysql_field')
        sync_vals = []
        
        if records:
            for rec in records:
                mysql_field = rec['Field']
                if mysql_field in existing_fields:
                    continue

                # Fetch constraints for foreign keys
                constraints = self.mysql_connect(
                    f"SELECT CONSTRAINT_NAME, COLUMN_NAME,"
                    f" REFERENCED_TABLE_NAME, "
                    f"REFERENCED_COLUMN_NAME FROM "
                    f"INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                    f"WHERE TABLE_NAME = "
                    f"'{self.sql_table}' and COLUMN_NAME = "
                    f"'{mysql_field}' and REFERENCED_TABLE_NAME IS NOT NULL and "
                    f"REFERENCED_COLUMN_NAME IS NOT NULL")
                
                vals = {
                    'connection_id': self.id,
                    'data_type': rec['Type'],
                    'mysql_field': mysql_field,
                    'model_id': self.model_id.id,
                    'foreign_key': True if constraints else False
                }
                if constraints:
                    vals['ref_table'] = constraints[0]['REFERENCED_TABLE_NAME']
                    vals['ref_col'] = constraints[0]['REFERENCED_COLUMN_NAME']
                
                sync_vals.append((0, 0, vals))
            
            if sync_vals:
                self.write({'sync_ids': sync_vals})
            
            self.write({
                'state': 'fetched',
                'is_fetched': True
            })

    def mysql_connect(self, query):
        """Method for connecting with MySDB"""
        try:
            connection = mysql.connector.connect(
                host=self.credential_id.host,
                user=self.credential_id.user,
                password=self.credential_id._decrypt_password(),
                database=self.credential_id.name
            )
            if not connection.is_connected():
                raise ValidationError(f"Error connecting to MySDB")
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            self.is_fetched = True
            cursor.close()
            connection.close()
            return results
        except mysql.connector.Error as e:
            raise ValidationError(f"Error connecting to MySDB: {e}")
