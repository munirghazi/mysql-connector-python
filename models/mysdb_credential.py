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
    port = fields.Integer(string='Port', default=3306,
                          help='MySQL port (default 3306)')
    connect_timeout = fields.Integer(string='Connect Timeout (sec)', default=10,
                                     help='Connection timeout in seconds')
    ssl_mode = fields.Selection([
        ('disabled', 'Disabled'),
        ('required', 'Required')
    ], string='SSL Mode', default='disabled',
       help='Enable SSL if your MySQL server requires it')
    ssl_ca = fields.Char(string='SSL CA Path',
                         help='Path to CA certificate file (optional)')
    ssl_cert = fields.Char(string='SSL Cert Path',
                           help='Path to client certificate file (optional)')
    ssl_key = fields.Char(string='SSL Key Path',
                          help='Path to client key file (optional)')
    password = fields.Char(string='Password',
                           help='Password of My SDB connection', required=True,
                           groups='base.group_system')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        help='Company that owns this credential. Leave empty for shared access.'
    )
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

    def _is_already_encrypted(self, password):
        """Check if a password string is already Fernet-encrypted.
        Tries to decrypt it — if that succeeds, it's already encrypted."""
        if not password or not Fernet:
            return False
        try:
            key = self._get_encrypt_key()
            if not key:
                return False
            f = Fernet(key)
            f.decrypt(password.encode('utf-8'))
            return True
        except Exception:
            return False

    def _encrypt_password(self, password):
        if not password or not Fernet:
            return password
        # Guard against double-encryption: if we can already decrypt it,
        # the value is already encrypted — return it unchanged.
        if self._is_already_encrypted(password):
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

    def _build_connect_kwargs(self):
        """Build MySQL connection keyword arguments from this credential.
        Centralised so that all callers (connector, action_connect, etc.)
        use the same logic."""
        self.ensure_one()
        connect_kwargs = {
            'host': self.host,
            'user': self.user,
            'password': self._decrypt_password(),
            'database': self.name,
            'port': self.port or 3306,
            'connection_timeout': self.connect_timeout or 10,
        }
        if self.ssl_mode == 'required':
            connect_kwargs.update({
                'ssl_ca': self.ssl_ca or None,
                'ssl_cert': self.ssl_cert or None,
                'ssl_key': self.ssl_key or None,
            })
        return connect_kwargs

    def action_connect(self):
        """Method for connecting with MySDB"""
        try:
            connect_kwargs = self._build_connect_kwargs()
            connection = mysql.connector.connect(**connect_kwargs)
            if connection.is_connected():
                self.sudo().write({
                    'state': 'connect'
                })
                connection.close()
        except mysql.connector.Error as e:
            # Handle any connection errors
            raise ValidationError(f"Error connecting to MySDB: {e}")
