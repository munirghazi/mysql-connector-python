# -*- coding: utf-8 -*-
from odoo import fields, models


class MysdbSyncStatus(models.Model):
    _name = 'mysdb.sync.status'
    _description = 'MySDB Sync Status'
    _auto = False

    source_type = fields.Selection(
        [('connector', 'Connector'), ('api', 'API Source'), ('sheet', 'Sheet Source')],
        string='Source Type',
        readonly=True,
    )
    source_name = fields.Char(string='Source Name', readonly=True)
    sync_datetime = fields.Datetime(string='Sync DateTime', readonly=True)
    sync_status = fields.Selection(
        [('ok', 'OK'), ('error', 'Error'), ('none', 'None')],
        string='Sync Status',
        readonly=True,
    )
    sync_message = fields.Text(string='Sync Message', readonly=True)

    def init(self):
        def _table_exists(table_name):
            self.env.cr.execute("SELECT to_regclass(%s)", (table_name,))
            return bool(self.env.cr.fetchone()[0])

        self.env.cr.execute("DROP VIEW IF EXISTS mysdb_sync_status")

        sources = []
        if _table_exists("mysdb_connector"):
            sources.append("""
                    SELECT
                        'connector'::text AS source_type,
                        c.name AS source_name,
                        c.last_sync_date AS sync_datetime,
                        CASE
                            WHEN c.last_sync_date IS NULL THEN 'none'
                            WHEN c.last_sync_message ILIKE 'Error%' THEN 'error'
                            ELSE 'ok'
                        END AS sync_status,
                        c.last_sync_message AS sync_message
                    FROM mysdb_connector c
            """)

        if _table_exists("mysdb_api_source"):
            sources.append("""
                    SELECT
                        'api'::text AS source_type,
                        a.name AS source_name,
                        a.last_sync_at AS sync_datetime,
                        COALESCE(a.last_sync_status, 'none') AS sync_status,
                        a.last_sync_message AS sync_message
                    FROM mysdb_api_source a
            """)

        if _table_exists("mysdb_sheet_source"):
            sources.append("""
                    SELECT
                        'sheet'::text AS source_type,
                        s.name AS source_name,
                        s.last_sync_at AS sync_datetime,
                        COALESCE(s.last_sync_status, 'none') AS sync_status,
                        s.last_sync_message AS sync_message
                    FROM mysdb_sheet_source s
            """)

        if not sources:
            sources.append("""
                SELECT
                    NULL::text AS source_type,
                    NULL::text AS source_name,
                    NULL::timestamp AS sync_datetime,
                    NULL::text AS sync_status,
                    NULL::text AS sync_message
                WHERE false
            """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mysdb_sync_status AS (
                SELECT
                    row_number() OVER () AS id,
                    data.source_type,
                    data.source_name,
                    data.sync_datetime,
                    data.sync_status,
                    data.sync_message
                FROM (
                    %s
                ) data
            )
        """ % " UNION ALL ".join(sources))

