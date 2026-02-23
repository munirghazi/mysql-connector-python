# -*- coding: utf-8 -*-
from odoo import fields, models


class MysdbAffiliate(models.Model):
    _name = 'mysdb.affiliate'
    _description = 'MySDB Affiliate'
    _rec_name = 'affiliate_name'

    publish_url = fields.Char('Publish URL')
    affiliate_account = fields.Char('Affiliate Account')
    url_target = fields.Char('URL Target')
    product_id = fields.Char('Product ID')
    affiliate_name = fields.Char('Affiliate Name')


