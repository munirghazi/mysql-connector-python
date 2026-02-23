# -*- coding: utf-8 -*-
from odoo import fields, models


class MysdbOrderDetailQuantity(models.Model):
    _inherit = 'mysdb.order.detail'

    quantity = fields.Float('Quantity')
    product_ref_id = fields.Many2one(
        'mysdb.product',
        string='Product',
        ondelete='set null',
        index=True
    )
    product_id = fields.Char(
        string='Product ID',
        index=True,
        help="Raw product ID from source system. Populated directly during sync, "
             "regardless of whether the product exists in mysdb.product."
    )

