# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MysdbOrder(models.Model):
    _name = 'mysdb.order'
    _description = 'MySDB Orders'
    _rec_name = 'order_code'

    order_id = fields.Char('Order ID', required=True, index=True)
    order_code = fields.Char('Order Code')
    order_url = fields.Char('Order URL')
    store_id = fields.Char('Store ID')
    store_name = fields.Char('Store Name')
    store_url = fields.Char('Store URL')
    currency_code = fields.Char('Currency')
    customer_id = fields.Char('Customer ID')
    customer_name = fields.Char('Customer Name', index=True)
    customer_email = fields.Char('Customer Email')
    customer_mobile = fields.Char('Customer Mobile')
    is_quick_checkout_order = fields.Boolean('Quick Checkout')
    order_total = fields.Float('Order Total')
    order_total_string = fields.Char('Order Total String')
    has_different_transaction_currency = fields.Boolean('Diff Currency')
    transaction_currency_code = fields.Char('Trans Currency')
    payment_status = fields.Char('Payment Status', index=True)
    order_created_at = fields.Datetime('Order Created At', index=True)
    
    # New Missing Fields
    transaction_reference = fields.Char('Transaction Reference')
    transaction_amount = fields.Float('Transaction Amount')
    transaction_amount_string = fields.Char('Transaction Amount String')
    issue_date = fields.Datetime('Issue Date')
    is_potential_fraud = fields.Boolean('Potential Fraud')
    source = fields.Char('Source')
    source_code = fields.Char('Source Code')
    payment_method_name = fields.Char('Payment Method Name')
    payment_method_code = fields.Char('Payment Method Code')
    payment_method_type = fields.Char('Payment Method Type')
    order_updated_at = fields.Datetime('Order Updated At')
    created_at = fields.Datetime('Created At')
    updated_at = fields.Datetime('Updated At')

class MysdbStore(models.Model):
    _name = 'mysdb.store'
    _description = 'MySDB Stores'
    _rec_name = 'store_name_ar'

    store_code = fields.Char('Store Code', required=True, index=True)
    store_name_ar = fields.Char('Store Name (AR)')
    store_name_en = fields.Char('Store Name (EN)')

    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('store_code', 'store_name_ar')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.store_code or 'N/A'}] {rec.store_name_ar or 'Unnamed'}"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            name_domain = ['|', ('store_code', '=', name), ('store_name_ar', operator, name)]
            return self._search(name_domain + domain, limit=limit, order=order)
        return super()._name_search(name, domain, operator, limit, order)

class MysdbOrderDetail(models.Model):
    _name = 'mysdb.order.detail'
    _description = 'MySDB Order Details'
    _rec_name = 'product_name'

    order_linked_id = fields.Char('Order Linked ID', index=True)
    product_name = fields.Char('Product Name')
    product_sku = fields.Char('Product SKU', index=True)
    total = fields.Float('Total')
    currency_code = fields.Char('Currency')
    store_id = fields.Char('Store ID')

class MysdbProduct(models.Model):
    _name = 'mysdb.product'
    _description = 'MySDB Products'
    _rec_name = 'product_name'

    product_id = fields.Char('Product ID', required=True, index=True)
    product_name = fields.Char('Product Name')
    product_name_ar = fields.Char('Product Name (AR)')
    product_sku = fields.Char('Product SKU', index=True)
    product_slug = fields.Char('Product Slug')
    store_id = fields.Char('Store ID')
    product_price = fields.Float('Price')
    product_quantity = fields.Float('Quantity')
    
    display_name = fields.Char(compute='_compute_display_name', store=False)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            # Look up by product_id first
            name_domain = ['|', ('product_id', '=', name), ('product_name', operator, name)]
            if operator in ['ilike', 'like', '=']:
                name_domain = ['|', ('product_id', '=', name), ('product_name', operator, name)]
            return self._search(name_domain + domain, limit=limit, order=order)
        return super()._name_search(name, domain, operator, limit, order)

    @api.depends('product_id', 'product_name', 'product_name_ar', 'product_slug')
    def _compute_display_name(self):
        for rec in self:
            # Use sudo to fetch name safely to avoid recursion during access checks
            r = rec.sudo()
            name = r.product_name_ar or r.product_name or 'Unnamed Product'
            rec.display_name = f"[{r.product_id or 'N/A'}] {name}"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        try:
            if self._context.get('filter_used_products'):
                self.env.cr.execute("SELECT product_id FROM mysdb_product_relation WHERE product_id IS NOT NULL")
                used_ids = [r[0] for r in self.env.cr.fetchall()]
                
                active_id = self._context.get('active_id') or self._context.get('id')
                if not active_id and 'params' in self._context:
                    active_id = self._context['params'].get('id')

                if active_id and isinstance(active_id, int):
                    self.env.cr.execute("SELECT product_id FROM mysdb_product_relation WHERE id = %s", (active_id,))
                    res = self.env.cr.fetchone()
                    if res and res[0]:
                        used_ids = [uid for uid in used_ids if uid != res[0]]
                
                if used_ids:
                    domain = [('id', 'not in', used_ids)] + domain
        except Exception:
            pass
        return super()._search(domain, offset, limit, order, access_rights_uid)

class MysdbSection(models.Model):
    _name = 'mysdb.section'
    _description = 'MySDB Sections'
    _rec_name = 'section_name_ar'

    section_id_mysdb = fields.Char('Section ID', required=True, index=True)
    section_name_ar = fields.Char('Section Name (AR)')
    section_name_en = fields.Char('Section Name (EN)')
    
    display_name = fields.Char(compute='_compute_display_name')

    def _compute_display_name(self):
        for rec in self:
            r = rec.sudo()
            rec.display_name = f"[{r.section_id_mysdb or 'N/A'}] {r.section_name_ar or 'Unnamed'}"

class MysdbProject(models.Model):
    _name = 'mysdb.project'
    _description = 'MySDB Projects'
    _rec_name = 'project_name_ar'

    project_id_mysdb = fields.Char('Project ID', required=True, index=True)
    project_name_ar = fields.Char('Project Name (AR)')
    project_name_en = fields.Char('Project Name (EN)')
    section_id = fields.Many2one('mysdb.section', string='Section', required=True)
    project_year = fields.Char('Year')
    project_starting_period = fields.Char('Starting Period')
    project_ending_period = fields.Char('Ending Period')
    
    display_name = fields.Char(compute='_compute_display_name')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            name_domain = ['|', ('project_id_mysdb', '=', name), ('project_name_ar', operator, name)]
            return self._search(name_domain + domain, limit=limit, order=order)
        return super()._name_search(name, domain, operator, limit, order)

    def _compute_display_name(self):
        for rec in self:
            r = rec.sudo()
            rec.display_name = f"[{r.project_id_mysdb or 'N/A'}] {r.project_name_ar or 'Unnamed'}"

class MysdbMarketingChannel(models.Model):
    _name = 'mysdb.marketing_channel'
    _description = 'MySDB Marketing Channel'
    _rec_name = 'name_ar'

    channel_id_mysdb = fields.Char('Channel ID', required=True)
    channel_type = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('snapchat', 'SnapChat'),
        ('instagram', 'Instagram'),
        ('facebook', 'FaceBook'),
        ('affiliate', 'Affiliate'),
        ('x', 'X (Twitter)'),
        ('telegram', 'Telegram')
    ], string='Type', required=True)
    name_ar = fields.Char('Name (AR)')
    name_en = fields.Char('Name (EN)')
    
    display_name = fields.Char(compute='_compute_display_name')

    def _compute_display_name(self):
        for rec in self:
            r = rec.sudo()
            rec.display_name = f"[{r.channel_id_mysdb or 'N/A'}] {r.name_ar or r.name_en or 'Unnamed'}"

class MysdbMarketingAccount(models.Model):
    _name = 'mysdb.marketing_account'
    _description = 'MySDB Marketing Account'
    _rec_name = 'name_ar'

    channel_id = fields.Many2one('mysdb.marketing_channel', string='Channel', required=True)
    account_id_mysdb = fields.Char('Account ID', required=True, index=True)
    name_ar = fields.Char('Name (AR)')
    name_en = fields.Char('Name (EN)')
    
    display_name = fields.Char(compute='_compute_display_name')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            name_domain = ['|', ('account_id_mysdb', '=', name), ('name_ar', operator, name)]
            return self._search(name_domain + domain, limit=limit, order=order)
        return super()._name_search(name, domain, operator, limit, order)

    def _compute_display_name(self):
        for rec in self:
            r = rec.sudo()
            rec.display_name = f"[{r.account_id_mysdb or 'N/A'}] {r.name_ar or r.name_en or 'Unnamed'}"

class MysdbProductRelation(models.Model):
    _name = 'mysdb.product_relation'
    _description = 'MySDB Product Relations'
    _rec_name = 'id'

    product_id = fields.Many2one('mysdb.product', string='Product', required=True, ondelete='cascade')
    project_id = fields.Many2one('mysdb.project', string='Project', ondelete='set null')
    
    display_name = fields.Char(compute='_compute_display_name')

    def _compute_display_name(self):
        for rec in self:
            if rec.product_id:
                p = rec.product_id.sudo()
                name = p.product_name_ar or p.product_name or 'Unnamed Product'
                rec.display_name = f"Relation: {name}"
            else:
                rec.display_name = f"New Relation ({rec.id})"

    _sql_constraints = [
        ('product_id_unique', 'unique(product_id)', 'A product can only be linked to one relation!')
    ]

class MysdbProductMarketingRelation(models.Model):
    _name = 'mysdb.product_marketing_relation'
    _description = 'MySDB Product Marketing Relations'
    _rec_name = 'id'

    product_id = fields.Many2one('mysdb.product', string='Product', required=True, ondelete='cascade')
    account_id = fields.Many2one('mysdb.marketing_account', string='Marketing Account', required=True, ondelete='cascade')
    
    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('product_id', 'account_id')
    def _compute_display_name(self):
        for rec in self:
            p = rec.product_id.sudo()
            a = rec.account_id.sudo()
            p_name = p.product_name_ar or p.product_name or 'No Product'
            a_name = a.name_ar or a.name_en or 'No Account'
            rec.display_name = f"{p_name} @ {a_name}"

    _sql_constraints = [
        ('product_account_unique', 'unique(product_id, account_id)', 'This product is already linked to this marketing account!')
    ]

class MysdbPeriodTargetCost(models.Model):
    _name = 'mysdb.period_target_cost'
    _description = 'MySDB Period Target Cost'
    _rec_name = 'period'

    period = fields.Selection([
        ('202500', '2025-00'), ('202501', '2025-01'), ('202502', '2025-02'), ('202503', '2025-03'),
        ('202504', '2025-04'), ('202505', '2025-05'), ('202506', '2025-06'), ('202507', '2025-07'),
        ('202508', '2025-08'), ('202509', '2025-09'), ('202510', '2025-10'), ('202511', '2025-11'),
        ('202512', '2025-12'),
        ('202600', '2026-00'), ('202601', '2026-01'), ('202602', '2026-02'), ('202603', '2026-03'),
        ('202604', '2026-04'), ('202605', '2026-05'), ('202606', '2026-06'), ('202607', '2026-07'),
        ('202608', '2026-08'), ('202609', '2026-09'), ('202610', '2026-10'), ('202611', '2026-11'),
        ('202612', '2026-12')
    ], string='Period')
    
    target_object = fields.Reference(
        selection=[
            ('mysdb.section', 'Section'), 
            ('mysdb.project', 'Project'),
            ('mysdb.marketing_account', 'Marketing Account')
        ],
        string="Target Object",
        required=True
    )
    
    object_id = fields.Char('Object ID', compute='_compute_object_id', store=True)
    target = fields.Float('Target')
    cost = fields.Float('Cost')

    @api.depends('target_object')
    def _compute_object_id(self):
        for rec in self:
            if rec.target_object:
                obj = rec.target_object.sudo()
                try:
                    if obj._name == 'mysdb.section':
                        rec.object_id = obj.section_id_mysdb
                    elif obj._name == 'mysdb.project':
                        rec.object_id = obj.project_id_mysdb
                    elif obj._name == 'mysdb.marketing_account':
                        rec.object_id = obj.account_id_mysdb
                    else:
                        rec.object_id = False
                except Exception:
                    rec.object_id = False
            else:
                rec.object_id = False

    display_name = fields.Char(compute='_compute_display_name')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"Target: {rec.period or 'No Period'} ({rec.object_id or 'No ID'})"

class MysdbPos(models.Model):
    _name = 'mysdb.pos'
    _description = 'MySDB Point of Sales'
    _rec_name = 'pos_name_en'

    pos_name_ar = fields.Char('POS Name (AR)')
    pos_name_en = fields.Char('POS Name (EN)')
    pos_name_sales_person = fields.Char('Sales Person')
    project_id = fields.Char('Project ID')
    section_id = fields.Char('Section ID')
    pos_name_sales_person_phone_no = fields.Char('Sales Person Phone')
    pos_name_sales_person_zid_id = fields.Char('Sales Person Zid ID')
    product_id = fields.Char('Product ID', index=True)
    mysdb_created_at = fields.Datetime('Created At')
    mysdb_updated_at = fields.Datetime('Updated At')

class MysdbOrderReport(models.Model):
    _name = 'mysdb.order.report'
    _description = 'MySDB Combined Order Analysis'
    _auto = False
    _rec_name = 'order_code'

    order_code = fields.Char('Order Code', readonly=True)
    order_created_at = fields.Datetime('Order Created At', readonly=True)
    customer_name = fields.Char('Customer', readonly=True)
    product_name = fields.Char('Product', readonly=True)
    product_sku = fields.Char('SKU', readonly=True)
    product_slug = fields.Char('Product Slug', readonly=True)
    line_total = fields.Float('Line Total', readonly=True)
    order_total = fields.Float('Order Total', readonly=True)
    payment_status = fields.Char('Status', readonly=True)
    store_name = fields.Char('Store', readonly=True)
    project_name_ar = fields.Char('Project (AR)', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS mysdb_order_report")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mysdb_order_report AS (
                SELECT 
                    d.id as id,
                    COALESCE(o.order_code, 'N/A') as order_code,
                    CAST(o.order_created_at AS TIMESTAMP) as order_created_at,
                    COALESCE(o.customer_name, 'Unknown') as customer_name,
                    COALESCE(d.product_name, 'No Product') as product_name,
                    d.product_sku as product_sku,
                    p.product_slug as product_slug,
                    COALESCE(d.total, 0.0) as line_total,
                    COALESCE(o.order_total, 0.0) as order_total,
                    COALESCE(o.payment_status, 'Unknown') as payment_status,
                    COALESCE(o.store_name, 'Unknown') as store_name,
                    COALESCE(proj.project_name_ar, 'No Project') as project_name_ar
                FROM mysdb_order_detail d
                LEFT JOIN mysdb_order o ON d.order_linked_id = o.order_id
                LEFT JOIN mysdb_product p ON (d.product_sku = p.product_sku AND d.store_id = p.store_id)
                LEFT JOIN mysdb_product_relation pr ON p.id = pr.product_id
                LEFT JOIN mysdb_project proj ON pr.project_id = proj.id
            )
        """)

    display_name = fields.Char(compute='_compute_display_name')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"Report Line: {rec.order_code or 'N/A'}"
