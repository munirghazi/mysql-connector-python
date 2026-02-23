# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MysdbOrderDetailLinkProductWizard(models.TransientModel):
    _name = 'mysdb.order.detail.link.product.wizard'
    _description = 'Link Order Details to Products'

    match_strategy = fields.Selection([
        ('sku_store', 'Product SKU + Store ID'),
        ('sku', 'Product SKU'),
        ('name_store', 'Product Name + Store ID'),
        ('name', 'Product Name'),
    ], string='Match Strategy', default='sku_store', required=True)
    fallback_to_name = fields.Boolean(
        string='Fallback to Product Name',
        default=True,
        help='If no SKU match is found, try matching by product name.'
    )
    overwrite_existing = fields.Boolean(
        string='Overwrite Existing Links',
        default=False,
        help='If enabled, existing product links will be replaced.'
    )
    only_missing = fields.Boolean(
        string='Only Missing Product Links',
        default=True,
        help='If enabled, only order details without a product link are updated.'
    )

    def _get_active_domain(self):
        active_ids = self.env.context.get('active_ids') or []
        if active_ids:
            return [('id', 'in', active_ids)]
        return []

    def _find_product(self, detail):
        Product = self.env['mysdb.product'].sudo()
        sku = (detail.product_sku or '').strip()
        name = (detail.product_name or '').strip()
        store_id = (detail.store_id or '').strip()

        def _search_by(domain):
            return Product.search(domain, limit=1)

        def _normalize_name(value):
            if not value:
                return ''
            text = str(value).replace('\u00A0', ' ').replace('ـ', ' ')
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        def _search_by_name(raw_name, store_code=None):
            normalized = _normalize_name(raw_name)
            if not normalized:
                return False
            token = normalized.split()[0]
            domain = []
            if store_code:
                domain.append(('store_id', '=', store_code))
            domain += ['|', ('product_name', 'ilike', token), ('product_name_ar', 'ilike', token)]
            candidates = Product.search(domain, limit=50)
            for cand in candidates:
                if _normalize_name(cand.product_name) == normalized:
                    return cand
                if _normalize_name(cand.product_name_ar) == normalized:
                    return cand
            return False

        if self.match_strategy == 'sku_store' and sku and store_id:
            product = _search_by([('product_sku', '=', sku), ('store_id', '=', store_id)])
            if product:
                return product
            if self.fallback_to_name and name:
                return _search_by_name(name, store_id)
        elif self.match_strategy == 'sku' and sku:
            product = _search_by([('product_sku', '=', sku)])
            if product:
                return product
            if self.fallback_to_name and name:
                return _search_by_name(name)
        elif self.match_strategy == 'name_store' and name and store_id:
            return _search_by_name(name, store_id)
        elif self.match_strategy == 'name' and name:
            return _search_by_name(name)
        return False

    def action_link_products(self):
        OrderDetail = self.env['mysdb.order.detail'].sudo()
        domain = self._get_active_domain()
        details = OrderDetail.search(domain) if domain else OrderDetail.search([])

        updated = 0
        skipped = 0

        for detail in details:
            if self.only_missing and detail.product_ref_id:
                skipped += 1
                continue
            if detail.product_ref_id and not self.overwrite_existing:
                skipped += 1
                continue

            product = self._find_product(detail)
            if product:
                detail.write({'product_ref_id': product.id})
                updated += 1
            else:
                skipped += 1

        _logger.info(
            "Link Products done: updated=%s skipped=%s total=%s",
            updated, skipped, len(details)
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Link Products'),
                'message': _('Updated: %s, Skipped: %s') % (updated, skipped),
                'type': 'success',
                'sticky': False,
            }
        }

