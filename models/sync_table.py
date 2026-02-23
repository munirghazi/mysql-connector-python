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
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SyncTable(models.Model):
    """Model holding the sync details"""
    _name = 'sync.table'
    _description = 'Sync Table'

    mysql_field = fields.Char(
        string='MySQL Field',
        help='Name of the field in MySQL database (legacy)'
    )
    mysql_field_id = fields.Many2one(
        'mysdb.mysql.column',
        string='MySQL Field',
        domain="[('connection_id', '=', connection_id)]",
        help='Select a field from the MySQL table.'
    )
    data_type = fields.Char(string='Datatype',
                            help='Data type of the field in MySQL')
    connection_id = fields.Many2one('mysdb.connector', string='Connection',
                                    help='Connection corresponds to mapping')
    model_id = fields.Many2one(string='Model Name', help='Name of the model',
                               related='connection_id.model_id')
    ir_field_id = fields.Many2one('ir.model.fields', string='Odoo Field',
                                  help='Name of the field in Odoo model',
                                  domain="[('model_id', '=', model_id)]")
    constant_value = fields.Char(
        string='Constant Value',
        help='Literal value to set on the Odoo field when Mapping Mode is Constant.'
    )
    formula_expression = fields.Char(
        string='Formula Expression',
        help="Expression using MySDB field names, e.g. 'qty * price'."
    )
    ref_table = fields.Char(string='Reference Table',
                            help='Name of the reference table in MySQL')
    ref_col = fields.Char(string='Reference Column',
                          help='Id of the reference table in MySQL')
    ref_col_name = fields.Char(string='Name of the Column in Reference Table',
                               help='Name of the column in reference table'
                                    ' to which the records to be compared')
    foreign_key = fields.Boolean(string='Foreign Key',
                                 help='True for for foreign keys')
    unique = fields.Char(string='Unique', help='Name of Unique field')
    # Legacy boolean fields — kept for backward compatibility with existing DB records.
    # New records should use mapping_mode instead.
    use_constant = fields.Boolean(string='Use Constant (deprecated)', default=False)
    use_formula = fields.Boolean(string='Use Formula (deprecated)', default=False)
    mapping_mode = fields.Selection(
        [
            ('mysql', 'MySQL Field'),
            ('constant', 'Constant'),
            ('formula', 'Formula'),
        ],
        string='Mapping Mode',
        default='mysql',
        required=True,
        help='Choose how to provide the value for the Odoo field.'
    )

    @api.constrains('mapping_mode', 'constant_value', 'formula_expression')
    def _check_mapping_mode_requirements(self):
        for rec in self:
            if rec.mapping_mode == 'constant' and not rec.constant_value:
                raise ValidationError("Constant Value is required when Mapping Mode is Constant.")
            if rec.mapping_mode == 'formula' and not rec.formula_expression:
                raise ValidationError("Formula Expression is required when Mapping Mode is Formula.")


class MysdbMysqlColumn(models.Model):
    _name = 'mysdb.mysql.column'
    _description = 'MySQL Column'

    name = fields.Char(string='Column Name', required=True, index=True)
    connection_id = fields.Many2one(
        'mysdb.connector',
        string='Connector',
        required=True,
        ondelete='cascade'
    )
