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
from odoo import fields, models, api
from odoo.exceptions import ValidationError
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

class MysdbCredential(models.Model):
    """Model holding MySDB credentials"""
    _name = 'mysdb.credential'
    _description = 'MySDB Credential'

    name = fields.Char(string='Database', help='Name of the database',
                       required=True)
    user = fields.Char(string='Username', help='Username of connection',
                       required=True)
    host = fields.Char(string='Host', help='Host name of MySDB connection',
                       required=True)
    password = fields.Char(string='Password',
                           help='Password of My SDB connection', required=True,
                           groups='base.group_system')
    state = fields.Selection([('draft', 'Draft'),
                              ('connect', 'Connected')],
                             string='State', help='State of the record',
                             readonly=True, default='draft')

    def _get_encrypt_key(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        key = ICPSudo.get_param('mysdb_connector.encrypt_key')
        if not key:
            if Fernet:
                key = Fernet.generate_key().decode('utf-8')
                ICPSudo.set_param('mysdb_connector.encrypt_key', key)
            else:
                return None
        return key.encode('utf-8')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'password' in vals:
                vals['password'] = self._encrypt_password(vals['password'])
        return super(MysdbCredential, self).create(vals_list)

    def write(self, vals):
        if 'password' in vals:
            vals['password'] = self._encrypt_password(vals['password'])
        return super(MysdbCredential, self).write(vals)

    def _encrypt_password(self, password):
        if not password or not Fernet:
            return password
        key = self._get_encrypt_key()
        if not key:
            return password
        f = Fernet(key)
        return f.encrypt(password.encode('utf-8')).decode('utf-8')

    def _decrypt_password(self):
        self.ensure_one()
        if not self.password or not Fernet:
            return self.password
        try:
            key = self._get_encrypt_key()
            if not key:
                return self.password
            f = Fernet(key)
            return f.decrypt(self.password.encode('utf-8')).decode('utf-8')
        except Exception:
            return self.password

    def action_connect(self):
        """Method for connecting with MySDB"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self._decrypt_password(),
                database=self.name
            )
            if connection.is_connected():
                self.sudo().write({
                    'state': 'connect'
                })
                connection.close()
        except mysql.connector.Error as e:
            # Handle any connection errors
            raise ValidationError(f"Error connecting to MySDB: {e}")
