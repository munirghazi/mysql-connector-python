# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MysdbOrderDetailLinkProductWizard(models.TransientModel):
    _name = 'mysdb.order.detail.link.product.wizard'
    _description = 'Link Order Details to Products'

    match_strategy = fields.Selection([
        ('name_ar_store', 'Product Name → Name AR + Store (Bayan)'),
        ('product_id_store', 'Product ID + Store ID'),
        ('product_id', 'Product ID'),
        ('sku_store', 'Product SKU + Store ID'),
        ('sku', 'Product SKU'),
        ('name_store', 'Product Name + Store ID'),
        ('name', 'Product Name'),
    ], string='Match Strategy', default='name_ar_store', required=True)
    strip_bayan_suffix = fields.Boolean(
        string='Strip Suffixes Before Matching',
        default=True,
        help='Remove configured suffixes (e.g. " - تبرع سريع") from order detail '
             'product name before matching against product_name_ar.'
    )
    strip_suffixes_list = fields.Text(
        string='Suffixes to Strip (one per line)',
        default='تبرع سريع\nتسويق\nإعادة استهداف',
        help="Suffixes to remove from the product name before matching.\n"
             "One suffix per line. The ' - ' dash before each suffix is "
             "stripped automatically.\n"
             "Example: 'name - رؤيا - تبرع سريع' with suffix 'تبرع سريع' "
             "becomes 'name - رؤيا'."
    )
    strip_quotes = fields.Boolean(
        string='Strip Surrounding Quotes',
        default=True,
        help='Remove leading/trailing quotes from the product name before matching.'
    )
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

    def _get_strip_suffixes(self):
        """Return the list of suffixes to strip, parsed from strip_suffixes_list."""
        raw = self.strip_suffixes_list or ''
        return [s.strip() for s in raw.splitlines() if s.strip()]

    def _clean_name(self, name):
        """Clean a product name using configured suffix list and quote-stripping."""
        from odoo.addons.my_sdb_reporting.models.mysdb_api_source import MysdbApiSource
        return MysdbApiSource._clean_product_name(
            name,
            suffixes=self._get_strip_suffixes(),
            strip_quotes=self.strip_quotes,
        )

    def _find_product(self, detail):
        Product = self.env['mysdb.product'].sudo()
        pid = (detail.product_id or '').strip()
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

        def _search_by_name_ar(raw_name, store_code=None):
            """Match against product_name_ar (Arabic) only."""
            cleaned = self._clean_name(raw_name) if self.strip_bayan_suffix else raw_name
            normalized = _normalize_name(cleaned)
            if not normalized:
                return False
            token = normalized.split()[0]
            domain = [('product_name_ar', 'ilike', token)]
            if store_code:
                domain.append(('store_id', '=', store_code))
            candidates = Product.search(domain, limit=100)
            for cand in candidates:
                if _normalize_name(cand.product_name_ar) == normalized:
                    return cand
            return False

        def _search_by_name(raw_name, store_code=None):
            """Match against product_name and product_name_ar."""
            search_name = self._clean_name(raw_name) if self.strip_bayan_suffix else raw_name
            normalized = _normalize_name(search_name)
            if not normalized:
                return False
            token = normalized.split()[0]
            domain = []
            if store_code:
                domain.append(('store_id', '=', store_code))
            domain += ['|', ('product_name', 'ilike', token), ('product_name_ar', 'ilike', token)]
            candidates = Product.search(domain, limit=100)
            for cand in candidates:
                if _normalize_name(cand.product_name) == normalized:
                    return cand
                if _normalize_name(cand.product_name_ar) == normalized:
                    return cand
            return False

        # --- Bayan: Name AR + Store strategy ---
        if self.match_strategy == 'name_ar_store' and name and store_id:
            return _search_by_name_ar(name, store_id)
        # --- Product ID strategies ---
        elif self.match_strategy == 'product_id_store' and pid and store_id:
            product = _search_by([('product_id', '=', pid), ('store_id', '=', store_id)])
            if product:
                return product
            if self.fallback_to_name and name:
                return _search_by_name(name, store_id)
        elif self.match_strategy == 'product_id' and pid:
            product = _search_by([('product_id', '=', pid)])
            if product:
                return product
            if self.fallback_to_name and name:
                return _search_by_name(name)
        # --- SKU strategies ---
        elif self.match_strategy == 'sku_store' and sku and store_id:
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
        # --- Name strategies ---
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
                detail.write({
                    'product_ref_id': product.id,
                    'product_id': product.product_id,
                })
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

