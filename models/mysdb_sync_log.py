# -*- coding: utf-8 -*-
from odoo import fields, models


class MysdbSyncLog(models.Model):
    _name = 'mysdb.sync.log'
    _description = 'MySDB Sync Log'
    _order = 'sync_datetime desc, id desc'

    source_type = fields.Selection(
        [('connector', 'Connector'), ('api', 'API Source'), ('sheet', 'Sheet Source')],
        string='Source Type',
        required=True,
        index=True,
    )
    source_name = fields.Char(string='Source Name', required=True, index=True)
    sync_datetime = fields.Datetime(string='Sync DateTime', required=True, index=True)
    sync_status = fields.Selection(
        [('ok', 'OK'), ('error', 'Error')],
        string='Sync Status',
        required=True,
        index=True,
    )
    sync_message = fields.Text(string='Sync Message')

