# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import calendar
from datetime import datetime

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
    
    # Newly added fields
    invoice_link = fields.Char('Invoice Link')
    order_detail_uuid = fields.Char('Order Detail UUID', index=True)
    created_at = fields.Datetime('Created At')
    updated_at = fields.Datetime('Updated At')

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
    
    # Assignment Status Tracking
    has_project = fields.Boolean('Has Project', compute='_compute_assignment_status', store=True, 
                                   help="Indicates if product is assigned to a project")
    has_marketing = fields.Boolean('Has Marketing Account', compute='_compute_assignment_status', store=True,
                                     help="Indicates if product is assigned to marketing account(s)")
    assignment_status = fields.Selection([
        ('complete', 'Complete Assignment'),
        ('partial', 'Partial Assignment'),
        ('none', 'No Assignment')
    ], string='Assignment Status', compute='_compute_assignment_status', store=True,
       help="Complete: Has both project and marketing | Partial: Has one | None: Has neither")
    
    project_relation_id = fields.One2many('mysdb.product_relation', 'product_id', string='Project Relation')
    marketing_relation_ids = fields.One2many('mysdb.product_marketing_relation', 'product_id', string='Marketing Relations')
    
    @api.depends('project_relation_id', 'marketing_relation_ids')
    def _compute_assignment_status(self):
        for rec in self:
            has_project = bool(rec.project_relation_id)
            has_marketing = bool(rec.marketing_relation_ids)
            
            rec.has_project = has_project
            rec.has_marketing = has_marketing
            
            if has_project and has_marketing:
                rec.assignment_status = 'complete'
            elif has_project or has_marketing:
                rec.assignment_status = 'partial'
            else:
                rec.assignment_status = 'none'

    @api.depends('product_id', 'product_name', 'store_id')
    def _compute_display_name(self):
        for rec in self:
            # Use sudo to fetch name safely to avoid recursion during access checks
            r = rec.sudo()
            # Show Store ID, Product ID and English Product Name
            rec.display_name = f"[{r.store_id or '?'}] [{r.product_id or 'N/A'}] {r.product_name or ''}"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        try:
            # Handle bulk assignment wizard filters
            if self._context.get('filter_assignment'):
                filter_assignment = self._context.get('filter_assignment')
                if filter_assignment == 'unassigned':
                    # Filter for products without project or marketing (depending on wizard type)
                    # Check if we're in project or marketing wizard by checking context
                    if 'default_project_id' in self._context or self._context.get('filter_type') == 'project':
                        domain = [('has_project', '=', False)] + domain
                    elif 'default_account_id' in self._context or self._context.get('filter_type') == 'marketing':
                        domain = [('has_marketing', '=', False)] + domain
                    else:
                        # Default to project filter
                        domain = [('has_project', '=', False)] + domain
                elif filter_assignment == 'incomplete':
                    domain = [('assignment_status', 'in', ['partial', 'none'])] + domain
                # 'all' means no additional filter
            
            if self._context.get('filter_store_id'):
                store_val = self._context.get('filter_store_id')
                if store_val:
                    # Handle different formats: int ID, tuple (id, name), or list [id]
                    store_rec_id = None
                    if isinstance(store_val, (list, tuple)) and len(store_val) > 0:
                        store_rec_id = store_val[0] if isinstance(store_val[0], int) else None
                    elif isinstance(store_val, int):
                        store_rec_id = store_val
                    
                    if store_rec_id:
                        # Resolve the store record ID to store_code
                        store_rec = self.env['mysdb.store'].browse(store_rec_id)
                        if store_rec and store_rec.store_code:
                            domain = [('store_id', '=', store_rec.store_code)] + domain
            
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
    store_id = fields.Many2one('mysdb.store', string='Store')

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
            # Show Store Code, Project ID and Arabic Project Name
            rec.display_name = f"[{r.store_id.store_code or '?'}] [{r.project_id_mysdb or 'N/A'}] {r.project_name_ar or 'Unnamed'}"

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
    _rec_name = 'product_id'

    product_id = fields.Many2one('mysdb.product', string='Product', required=True, ondelete='cascade')
    project_id = fields.Many2one('mysdb.project', string='Project', ondelete='set null')

    @api.constrains('product_id', 'project_id')
    def _check_store_match(self):
        for rec in self:
            if rec.product_id and rec.project_id:
                product_store = rec.product_id.sudo().store_id
                project_store = rec.project_id.sudo().store_id.store_code
                if product_store != project_store:
                    raise ValidationError(
                        f"Store Mismatch! \n\n"
                        f"Product '{rec.product_id.display_name}' belongs to Store ID: {product_store}\n"
                        f"Project '{rec.project_id.display_name}' belongs to Store ID: {project_store}\n\n"
                        f"Please ensure both belong to the same Store."
                    )

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
    
    # Helper fields for better tracking
    store_id = fields.Char('Store ID', related='product_id.store_id', store=True, readonly=True)
    channel_id = fields.Many2one('mysdb.marketing_channel', related='account_id.channel_id', store=True, readonly=True)
    
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
    
    @api.model
    def _get_period_selection(self):
        """Generate period selection dynamically from 2024 to current_year + 2"""
        current_year = datetime.now().year
        start_year = 2024
        end_year = current_year + 2
        
        periods = []
        for year in range(start_year, end_year + 1):
            # Yearly period
            periods.append((f'{year}00', f'{year}-00 (Yearly)'))
            # Monthly periods
            for month in range(1, 13):
                month_str = f'{month:02d}'
                month_name = calendar.month_abbr[month]
                periods.append((f'{year}{month_str}', f'{year}-{month_str} ({month_name})'))
        
        return periods

    period = fields.Selection(selection='_get_period_selection', string='Period', required=True, index=True)
    
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
    target = fields.Float('Target', required=True)
    cost = fields.Float('Cost')
    
    # Period Helper Fields
    period_year = fields.Char('Year', compute='_compute_period_info', store=True, index=True)
    period_month = fields.Char('Month', compute='_compute_period_info', store=True, index=True)
    is_yearly = fields.Boolean('Is Yearly', compute='_compute_period_info', store=True)
    period_type = fields.Selection([
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly')
    ], string='Period Type', compute='_compute_period_info', store=True)
    
    # Achievement Fields
    actual_income = fields.Float('Actual Income', compute='_compute_achievement', store=True)
    achievement_percent = fields.Float('Achievement %', compute='_compute_achievement', store=True)
    variance = fields.Float('Variance', compute='_compute_achievement', store=True)
    roi = fields.Float('ROI %', compute='_compute_achievement', store=True, 
                       help="Return on Investment: (Income - Cost) / Cost * 100")
    profit = fields.Float('Profit', compute='_compute_achievement', store=True,
                          help="Actual Income - Cost")
    
    @api.depends('period')
    def _compute_period_info(self):
        for rec in self:
            if rec.period and len(rec.period) == 6:
                rec.period_year = rec.period[:4]
                rec.period_month = rec.period[4:]
                rec.is_yearly = (rec.period[4:] == '00')
                rec.period_type = 'yearly' if rec.is_yearly else 'monthly'
            else:
                rec.period_year = False
                rec.period_month = False
                rec.is_yearly = False
                rec.period_type = False

    @api.depends('period', 'target_object', 'target')
    def _compute_achievement(self):
        for rec in self:
            income = 0.0
            if rec.period and rec.target_object:
                year = rec.period[:4]
                month = rec.period[4:]
                
                # Define Domain for Orders
                domain = [('payment_status', '=', 'paid')]
                if month == '00':
                    # Yearly
                    date_start = f"{year}-01-01 00:00:00"
                    date_end = f"{year}-12-31 23:59:59"
                else:
                    # Monthly
                    import calendar
                    last_day = calendar.monthrange(int(year), int(month))[1]
                    date_start = f"{year}-{month}-01 00:00:00"
                    date_end = f"{year}-{month}-{last_day} 23:59:59"
                
                domain += [('order_created_at', '>=', date_start), ('order_created_at', '<=', date_end)]
                
                # Find Order IDs in range
                orders = self.env['mysdb.order'].sudo().search(domain)
                order_ids = orders.mapped('order_id')
                
                if order_ids:
                    # Get relevant details
                    detail_domain = [('order_linked_id', 'in', order_ids)]
                    
                    if rec.target_object._name == 'mysdb.project':
                        # Project income: find products in this project
                        project_id = rec.target_object.id
                        self.env.cr.execute("""
                            SELECT p.product_sku 
                            FROM mysdb_product p
                            JOIN mysdb_product_relation pr ON p.id = pr.product_id
                            WHERE pr.project_id = %s
                        """, (project_id,))
                        skus = [r[0] for r in self.env.cr.fetchall()]
                        if skus:
                            detail_domain += [('product_sku', 'in', skus)]
                            details = self.env['mysdb.order.detail'].sudo().search(detail_domain)
                            income = sum(details.mapped('total'))
                            
                    elif rec.target_object._name == 'mysdb.marketing_account':
                        # Account income: find products in this account
                        account_id = rec.target_object.id
                        self.env.cr.execute("""
                            SELECT p.product_sku 
                            FROM mysdb_product p
                            JOIN mysdb_product_marketing_relation pmr ON p.id = pmr.product_id
                            WHERE pmr.account_id = %s
                        """, (account_id,))
                        skus = [r[0] for r in self.env.cr.fetchall()]
                        if skus:
                            detail_domain += [('product_sku', 'in', skus)]
                            details = self.env['mysdb.order.detail'].sudo().search(detail_domain)
                            income = sum(details.mapped('total'))
                            
                    elif rec.target_object._name == 'mysdb.section':
                        # Section income: find products in projects in this section
                        section_id = rec.target_object.id
                        self.env.cr.execute("""
                            SELECT p.product_sku 
                            FROM mysdb_product p
                            JOIN mysdb_product_relation pr ON p.id = pr.product_id
                            JOIN mysdb_project proj ON pr.project_id = proj.id
                            WHERE proj.section_id = %s
                        """, (section_id,))
                        skus = [r[0] for r in self.env.cr.fetchall()]
                        if skus:
                            detail_domain += [('product_sku', 'in', skus)]
                            details = self.env['mysdb.order.detail'].sudo().search(detail_domain)
                            income = sum(details.mapped('total'))

            rec.actual_income = income
            rec.achievement_percent = (income / rec.target * 100.0) if rec.target > 0 else 0.0
            rec.variance = income - rec.target
            rec.profit = income - rec.cost
            rec.roi = ((income - rec.cost) / rec.cost * 100.0) if rec.cost > 0 else 0.0

    # Helper fields for CSV Import
    import_type = fields.Selection([
        ('section', 'Section'),
        ('project', 'Project'),
        ('marketing_account', 'Marketing Account')
    ], string="Import Type (Use for CSV)")
    import_id = fields.Char(string="Import ID (Use for CSV)")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'import_type' in vals and 'import_id' in vals and not vals.get('target_object'):
                itype = vals.get('import_type')
                iid = vals.get('import_id')
                res_id = False
                
                if itype == 'project':
                    obj = self.env['mysdb.project'].sudo().search([('project_id_mysdb', '=', iid)], limit=1)
                    if obj: res_id = obj.id
                elif itype == 'section':
                    obj = self.env['mysdb.section'].sudo().search([('section_id_mysdb', '=', iid)], limit=1)
                    if obj: res_id = obj.id
                elif itype == 'marketing_account':
                    obj = self.env['mysdb.marketing_account'].sudo().search([('account_id_mysdb', '=', iid)], limit=1)
                    if obj: res_id = obj.id
                
                if res_id:
                    vals['target_object'] = f"mysdb.{itype},{res_id}"
        return super().create(vals_list)

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

    _sql_constraints = [
        ('period_object_unique', 'unique(period, target_object)', 'This object already has a target cost set for this period!')
    ]

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
    section_name_ar = fields.Char('Section (AR)', readonly=True)
    transaction_reference = fields.Char('Transaction Ref', readonly=True)
    payment_method_name = fields.Char('Payment Method', readonly=True)
    source = fields.Char('Source', readonly=True)
    order_detail_uuid = fields.Char('Detail UUID', readonly=True)
    invoice_link = fields.Char('Invoice Link', readonly=True)
    marketing_account_name_ar = fields.Char('Marketing Account (AR)', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS mysdb_order_report")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mysdb_order_report AS (
                -- 1. Actual Product Lines
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
                    COALESCE(proj.project_name_ar, 'No Project') as project_name_ar,
                    COALESCE(sect.section_name_ar, 'No Section') as section_name_ar,
                    o.transaction_reference as transaction_reference,
                    o.payment_method_name as payment_method_name,
                    o.source as source,
                    d.order_detail_uuid as order_detail_uuid,
                    d.invoice_link as invoice_link,
                    COALESCE(macc.name_ar, 'No Account') as marketing_account_name_ar
                FROM mysdb_order_detail d
                LEFT JOIN mysdb_order o ON d.order_linked_id = o.order_id
                LEFT JOIN mysdb_product p ON (d.product_sku = p.product_sku AND d.store_id = p.store_id)
                LEFT JOIN mysdb_product_relation pr ON p.id = pr.product_id
                LEFT JOIN mysdb_project proj ON pr.project_id = proj.id
                LEFT JOIN mysdb_section sect ON proj.section_id = sect.id
                LEFT JOIN mysdb_product_marketing_relation pmr ON p.id = pmr.product_id
                LEFT JOIN mysdb_marketing_account macc ON pmr.account_id = macc.id

                UNION ALL

                -- 2. Adjustment Lines (Shipping, VAT, Fees)
                -- We use a negative ID range to avoid conflict with detail IDs
                SELECT 
                    (o.id * -1) as id,
                    COALESCE(o.order_code, 'N/A') as order_code,
                    CAST(o.order_created_at AS TIMESTAMP) as order_created_at,
                    COALESCE(o.customer_name, 'Unknown') as customer_name,
                    'Adjustments (Shipping/Tax/Fees)' as product_name,
                    'ADJ' as product_sku,
                    'adjustment' as product_slug,
                    (o.order_total - COALESCE(lines.total_sum, 0.0)) as line_total,
                    o.order_total as order_total,
                    COALESCE(o.payment_status, 'Unknown') as payment_status,
                    COALESCE(o.store_name, 'Unknown') as store_name,
                    'Adjustments' as project_name_ar,
                    'Adjustments' as section_name_ar,
                    o.transaction_reference as transaction_reference,
                    o.payment_method_name as payment_method_name,
                    o.source as source,
                    'ADJ-' || o.order_id as order_detail_uuid,
                    '' as invoice_link,
                    'N/A' as marketing_account_name_ar
                FROM mysdb_order o
                LEFT JOIN (
                    SELECT order_linked_id, SUM(total) as total_sum 
                    FROM mysdb_order_detail 
                    GROUP BY order_linked_id
                ) lines ON o.order_id = lines.order_linked_id
                WHERE (o.order_total - COALESCE(lines.total_sum, 0.0)) != 0
            )
        """)

    display_name = fields.Char(compute='_compute_display_name')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"Report Line: {rec.order_code or 'N/A'}"

class MysdbProjectIncomeReport(models.Model):
    _name = 'mysdb.project.income.report'
    _description = 'Project Income Analysis Report'
    _auto = False
    _rec_name = 'project_name_ar'
    _order = 'period desc, total_income desc'

    project_id = fields.Integer('Project ID (Internal)', readonly=True)
    project_id_mysdb = fields.Char('Project ID', readonly=True)
    project_name_ar = fields.Char('Project Name (AR)', readonly=True)
    project_name_en = fields.Char('Project Name (EN)', readonly=True)
    section_name_ar = fields.Char('Section (AR)', readonly=True)
    store_code = fields.Char('Store Code', readonly=True)
    period = fields.Char('Period (YYYYMM)', readonly=True)
    period_year = fields.Char('Year', readonly=True)
    period_month = fields.Char('Month', readonly=True)
    total_income = fields.Float('Total Income', readonly=True)
    order_count = fields.Integer('Number of Orders', readonly=True)
    product_count = fields.Integer('Number of Products', readonly=True)
    target_amount = fields.Float('Target', readonly=True)
    cost_amount = fields.Float('Cost', readonly=True)
    achievement_percent = fields.Float('Achievement %', readonly=True)
    profit = fields.Float('Profit', readonly=True)
    roi = fields.Float('ROI %', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS mysdb_project_income_report")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mysdb_project_income_report AS (
                WITH order_income AS (
                    SELECT 
                        pr.project_id,
                        TO_CHAR(o.order_created_at, 'YYYYMM') as period,
                        SUM(d.total) as income,
                        COUNT(DISTINCT o.order_id) as order_count,
                        COUNT(DISTINCT p.id) as product_count
                    FROM mysdb_order o
                    JOIN mysdb_order_detail d ON o.order_id = d.order_linked_id
                    JOIN mysdb_product p ON d.product_sku = p.product_sku AND d.store_id = p.store_id
                    JOIN mysdb_product_relation pr ON p.id = pr.product_id
                    WHERE o.payment_status = 'paid'
                    GROUP BY pr.project_id, TO_CHAR(o.order_created_at, 'YYYYMM')
                ),
                targets AS (
                    SELECT 
                        CAST(SUBSTRING(target_object FROM 'mysdb.project,([0-9]+)') AS INTEGER) as project_id,
                        period,
                        target,
                        cost
                    FROM mysdb_period_target_cost
                    WHERE target_object LIKE 'mysdb.project,%'
                )
                SELECT 
                    ROW_NUMBER() OVER () as id,
                    proj.id as project_id,
                    proj.project_id_mysdb,
                    proj.project_name_ar,
                    proj.project_name_en,
                    sect.section_name_ar,
                    st.store_code,
                    oi.period,
                    SUBSTRING(oi.period, 1, 4) as period_year,
                    SUBSTRING(oi.period, 5, 2) as period_month,
                    COALESCE(oi.income, 0.0) as total_income,
                    COALESCE(oi.order_count, 0)::integer as order_count,
                    COALESCE(oi.product_count, 0)::integer as product_count,
                    COALESCE(t.target, 0.0) as target_amount,
                    COALESCE(t.cost, 0.0) as cost_amount,
                    CASE 
                        WHEN COALESCE(t.target, 0) > 0 THEN (COALESCE(oi.income, 0) / t.target * 100.0)
                        ELSE 0.0
                    END as achievement_percent,
                    (COALESCE(oi.income, 0.0) - COALESCE(t.cost, 0.0)) as profit,
                    CASE 
                        WHEN COALESCE(t.cost, 0) > 0 THEN ((COALESCE(oi.income, 0) - t.cost) / t.cost * 100.0)
                        ELSE 0.0
                    END as roi
                FROM mysdb_project proj
                LEFT JOIN mysdb_section sect ON proj.section_id = sect.id
                LEFT JOIN mysdb_store st ON proj.store_id = st.id
                CROSS JOIN (
                    SELECT DISTINCT period FROM order_income
                    UNION
                    SELECT DISTINCT period FROM targets
                ) periods
                LEFT JOIN order_income oi ON proj.id = oi.project_id AND periods.period = oi.period
                LEFT JOIN targets t ON proj.id = t.project_id AND periods.period = t.period
                WHERE oi.income IS NOT NULL OR t.target IS NOT NULL
            )
        """)

class MysdbMarketingIncomeReport(models.Model):
    _name = 'mysdb.marketing.income.report'
    _description = 'Marketing Account Income Analysis Report'
    _auto = False
    _rec_name = 'account_name_ar'
    _order = 'period desc, total_income desc'

    account_id = fields.Integer('Account ID (Internal)', readonly=True)
    account_id_mysdb = fields.Char('Account ID', readonly=True)
    account_name_ar = fields.Char('Account Name (AR)', readonly=True)
    account_name_en = fields.Char('Account Name (EN)', readonly=True)
    channel_name_ar = fields.Char('Channel (AR)', readonly=True)
    channel_type = fields.Char('Channel Type', readonly=True)
    period = fields.Char('Period (YYYYMM)', readonly=True)
    period_year = fields.Char('Year', readonly=True)
    period_month = fields.Char('Month', readonly=True)
    total_income = fields.Float('Total Income', readonly=True)
    order_count = fields.Integer('Number of Orders', readonly=True)
    product_count = fields.Integer('Number of Products', readonly=True)
    target_amount = fields.Float('Target', readonly=True)
    cost_amount = fields.Float('Cost', readonly=True)
    achievement_percent = fields.Float('Achievement %', readonly=True)
    profit = fields.Float('Profit', readonly=True)
    roi = fields.Float('ROI %', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS mysdb_marketing_income_report")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mysdb_marketing_income_report AS (
                WITH order_income AS (
                    SELECT 
                        pmr.account_id,
                        TO_CHAR(o.order_created_at, 'YYYYMM') as period,
                        SUM(d.total) as income,
                        COUNT(DISTINCT o.order_id) as order_count,
                        COUNT(DISTINCT p.id) as product_count
                    FROM mysdb_order o
                    JOIN mysdb_order_detail d ON o.order_id = d.order_linked_id
                    JOIN mysdb_product p ON d.product_sku = p.product_sku AND d.store_id = p.store_id
                    JOIN mysdb_product_marketing_relation pmr ON p.id = pmr.product_id
                    WHERE o.payment_status = 'paid'
                    GROUP BY pmr.account_id, TO_CHAR(o.order_created_at, 'YYYYMM')
                ),
                targets AS (
                    SELECT 
                        CAST(SUBSTRING(target_object FROM 'mysdb.marketing_account,([0-9]+)') AS INTEGER) as account_id,
                        period,
                        target,
                        cost
                    FROM mysdb_period_target_cost
                    WHERE target_object LIKE 'mysdb.marketing_account,%'
                )
                SELECT 
                    ROW_NUMBER() OVER () as id,
                    acc.id as account_id,
                    acc.account_id_mysdb,
                    acc.name_ar as account_name_ar,
                    acc.name_en as account_name_en,
                    ch.name_ar as channel_name_ar,
                    ch.channel_type,
                    oi.period,
                    SUBSTRING(oi.period, 1, 4) as period_year,
                    SUBSTRING(oi.period, 5, 2) as period_month,
                    COALESCE(oi.income, 0.0) as total_income,
                    COALESCE(oi.order_count, 0)::integer as order_count,
                    COALESCE(oi.product_count, 0)::integer as product_count,
                    COALESCE(t.target, 0.0) as target_amount,
                    COALESCE(t.cost, 0.0) as cost_amount,
                    CASE 
                        WHEN COALESCE(t.target, 0) > 0 THEN (COALESCE(oi.income, 0) / t.target * 100.0)
                        ELSE 0.0
                    END as achievement_percent,
                    (COALESCE(oi.income, 0.0) - COALESCE(t.cost, 0.0)) as profit,
                    CASE 
                        WHEN COALESCE(t.cost, 0) > 0 THEN ((COALESCE(oi.income, 0) - t.cost) / t.cost * 100.0)
                        ELSE 0.0
                    END as roi
                FROM mysdb_marketing_account acc
                LEFT JOIN mysdb_marketing_channel ch ON acc.channel_id = ch.id
                CROSS JOIN (
                    SELECT DISTINCT period FROM order_income
                    UNION
                    SELECT DISTINCT period FROM targets
                ) periods
                LEFT JOIN order_income oi ON acc.id = oi.account_id AND periods.period = oi.period
                LEFT JOIN targets t ON acc.id = t.account_id AND periods.period = t.period
                WHERE oi.income IS NOT NULL OR t.target IS NOT NULL
            )
        """)

class MysdbDataAudit(models.Model):
    _name = 'mysdb.data.audit'
    _description = 'MySDB Data Maintenance Audit'
    _auto = False

    issue_type = fields.Selection([
        ('missing_product', 'Product Missing from Catalog'),
        ('no_project', 'No Project Assigned'),
        ('no_marketing', 'No Marketing Account Assigned'),
        ('incomplete_assignment', 'Incomplete Assignment (Only Project OR Marketing)')
    ], string='Issue Category', readonly=True)
    
    product_sku = fields.Char('Product SKU', readonly=True)
    product_name = fields.Char('Product Name', readonly=True)
    store_id = fields.Char('Store ID', readonly=True)
    last_seen_order = fields.Char('Last Seen in Order', readonly=True)
    product_id_int = fields.Integer('Product ID (Internal)', readonly=True, 
                                     help="Internal product ID for quick navigation")
    total_order_value = fields.Float('Total Order Value', readonly=True,
                                      help="Total revenue from this product in paid orders")
    order_count = fields.Integer('Order Count', readonly=True,
                                  help="Number of paid orders containing this product")
    priority = fields.Selection([
        ('high', 'High - Has Recent Orders'),
        ('medium', 'Medium - Has Historical Orders'),
        ('low', 'Low - No Order History')
    ], string='Priority', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS mysdb_data_audit")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mysdb_data_audit AS (
                -- 1. Products in Order Details but NOT in Product Table
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(d.total), 0) DESC) as id,
                    'missing_product' as issue_type,
                    d.product_sku,
                    d.product_name,
                    d.store_id,
                    COALESCE(MAX(o.order_code), 'N/A') as last_seen_order,
                    NULL::integer as product_id_int,
                    COALESCE(SUM(CASE WHEN o.payment_status = 'paid' THEN d.total ELSE 0 END), 0.0) as total_order_value,
                    COUNT(DISTINCT CASE WHEN o.payment_status = 'paid' THEN o.order_id ELSE NULL END)::integer as order_count,
                    CASE 
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '30 days' THEN 'high'
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '90 days' THEN 'medium'
                        ELSE 'low'
                    END as priority
                FROM mysdb_order_detail d
                LEFT JOIN mysdb_order o ON d.order_linked_id = o.order_id
                WHERE d.product_sku NOT IN (SELECT product_sku FROM mysdb_product WHERE product_sku IS NOT NULL)
                  AND d.product_sku IS NOT NULL
                GROUP BY d.product_sku, d.product_name, d.store_id

                UNION ALL

                -- 2. Products in Table but NO Project Relation
                SELECT 
                    (ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(d.total), 0) DESC) + 1000000) as id,
                    'no_project' as issue_type,
                    p.product_sku,
                    p.product_name,
                    p.store_id,
                    COALESCE(MAX(o.order_code), 'N/A') as last_seen_order,
                    p.id as product_id_int,
                    COALESCE(SUM(CASE WHEN o.payment_status = 'paid' THEN d.total ELSE 0 END), 0.0) as total_order_value,
                    COUNT(DISTINCT CASE WHEN o.payment_status = 'paid' THEN o.order_id ELSE NULL END)::integer as order_count,
                    CASE 
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '30 days' THEN 'high'
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '90 days' THEN 'medium'
                        WHEN MAX(o.order_created_at) IS NOT NULL THEN 'low'
                        ELSE 'low'
                    END as priority
                FROM mysdb_product p
                LEFT JOIN mysdb_order_detail d ON p.product_sku = d.product_sku AND p.store_id = d.store_id
                LEFT JOIN mysdb_order o ON d.order_linked_id = o.order_id
                WHERE p.id NOT IN (SELECT product_id FROM mysdb_product_relation WHERE product_id IS NOT NULL)
                GROUP BY p.id, p.product_sku, p.product_name, p.store_id

                UNION ALL

                -- 3. Products in Table but NO Marketing Account Relation
                SELECT 
                    (ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(d.total), 0) DESC) + 2000000) as id,
                    'no_marketing' as issue_type,
                    p.product_sku,
                    p.product_name,
                    p.store_id,
                    COALESCE(MAX(o.order_code), 'N/A') as last_seen_order,
                    p.id as product_id_int,
                    COALESCE(SUM(CASE WHEN o.payment_status = 'paid' THEN d.total ELSE 0 END), 0.0) as total_order_value,
                    COUNT(DISTINCT CASE WHEN o.payment_status = 'paid' THEN o.order_id ELSE NULL END)::integer as order_count,
                    CASE 
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '30 days' THEN 'high'
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '90 days' THEN 'medium'
                        WHEN MAX(o.order_created_at) IS NOT NULL THEN 'low'
                        ELSE 'low'
                    END as priority
                FROM mysdb_product p
                LEFT JOIN mysdb_order_detail d ON p.product_sku = d.product_sku AND p.store_id = d.store_id
                LEFT JOIN mysdb_order o ON d.order_linked_id = o.order_id
                WHERE p.id NOT IN (SELECT product_id FROM mysdb_product_marketing_relation WHERE product_id IS NOT NULL)
                GROUP BY p.id, p.product_sku, p.product_name, p.store_id
                
                UNION ALL
                
                -- 4. Products with Incomplete Assignment (has project but no marketing OR has marketing but no project)
                SELECT 
                    (ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(d.total), 0) DESC) + 3000000) as id,
                    'incomplete_assignment' as issue_type,
                    p.product_sku,
                    p.product_name,
                    p.store_id,
                    COALESCE(MAX(o.order_code), 'N/A') as last_seen_order,
                    p.id as product_id_int,
                    COALESCE(SUM(CASE WHEN o.payment_status = 'paid' THEN d.total ELSE 0 END), 0.0) as total_order_value,
                    COUNT(DISTINCT CASE WHEN o.payment_status = 'paid' THEN o.order_id ELSE NULL END)::integer as order_count,
                    CASE 
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '30 days' THEN 'high'
                        WHEN MAX(o.order_created_at) >= NOW() - INTERVAL '90 days' THEN 'medium'
                        WHEN MAX(o.order_created_at) IS NOT NULL THEN 'low'
                        ELSE 'low'
                    END as priority
                FROM mysdb_product p
                LEFT JOIN mysdb_order_detail d ON p.product_sku = d.product_sku AND p.store_id = d.store_id
                LEFT JOIN mysdb_order o ON d.order_linked_id = o.order_id
                WHERE (
                    (p.id IN (SELECT product_id FROM mysdb_product_relation WHERE product_id IS NOT NULL) 
                     AND p.id NOT IN (SELECT product_id FROM mysdb_product_marketing_relation WHERE product_id IS NOT NULL))
                    OR
                    (p.id NOT IN (SELECT product_id FROM mysdb_product_relation WHERE product_id IS NOT NULL) 
                     AND p.id IN (SELECT product_id FROM mysdb_product_marketing_relation WHERE product_id IS NOT NULL))
                )
                GROUP BY p.id, p.product_sku, p.product_name, p.store_id
            )
        """)

class MysdbBulkAssignProjectWizard(models.TransientModel):
    _name = 'mysdb.bulk.assign.project.wizard'
    _description = 'Bulk Assign Products to Project'

    project_id = fields.Many2one('mysdb.project', string='Target Project', required=True,
                                  help="All selected products will be assigned to this project")
    product_ids = fields.Many2many('mysdb.product', string='Products to Assign',
                                     help="Select products to assign to the project")
    store_id = fields.Many2one('mysdb.store', string='Filter by Store',
                                help="Filter products by store for easier selection")
    assignment_filter = fields.Selection([
        ('all', 'All Products'),
        ('unassigned', 'Products Without Project'),
        ('incomplete', 'Products Without Complete Assignment')
    ], string='Filter Products', default='unassigned',
       help="Filter which products to show for selection")
    
    replace_existing = fields.Boolean('Replace Existing Project Assignment', default=False,
                                       help="If checked, will replace existing project assignment. Otherwise, skip products with existing project.")
    
    preview_count = fields.Integer('Products to Assign', compute='_compute_preview_count')
    
    @api.depends('product_ids')
    def _compute_preview_count(self):
        for wizard in self:
            wizard.preview_count = len(wizard.product_ids)
    
    @api.onchange('store_id', 'assignment_filter')
    def _onchange_filters(self):
        """Update product domain based on filters"""
        domain = []
        
        # Always add store filter if selected
        if self.store_id and self.store_id.store_code:
            domain.append(('store_id', '=', self.store_id.store_code))
        
        # Add assignment filter
        if self.assignment_filter == 'unassigned':
            domain.append(('has_project', '=', False))
        elif self.assignment_filter == 'incomplete':
            domain.append(('assignment_status', 'in', ['partial', 'none']))
        # 'all' means no additional assignment filter
        
        # If no filters, ensure we show something (empty domain = all products)
        if not domain:
            domain = [(1, '=', 1)]  # Always true
        
        # Clear selected products when filter changes
        self.product_ids = [(5, 0, 0)]
        
        # Return domain for both the field AND a warning to show domain is active
        result = {'domain': {'product_ids': domain}}
        
        # Add context to help with popup filtering
        if self.store_id or self.assignment_filter != 'all':
            filter_desc = []
            if self.store_id:
                filter_desc.append(f"Store: {self.store_id.display_name}")
            if self.assignment_filter == 'unassigned':
                filter_desc.append("Unassigned products only")
            elif self.assignment_filter == 'incomplete':
                filter_desc.append("Incomplete assignments only")
            
            # Note: This warning won't appear but ensures the onchange is processed
            result['warning'] = {
                'title': 'Filter Applied',
                'message': f"Active filters: {', '.join(filter_desc)}\nNote: Filters apply to product list below. Use search in popup if needed.",
                'type': 'notification'
            }
        
        return result
    
    def action_assign(self):
        """Execute bulk assignment"""
        self.ensure_one()
        
        if not self.product_ids:
            raise ValidationError("Please select at least one product to assign.")
        
        # Validate store match
        project_store = self.project_id.store_id.store_code
        for product in self.product_ids:
            if product.store_id != project_store:
                raise ValidationError(
                    f"Store Mismatch!\n\n"
                    f"Product '{product.display_name}' belongs to Store: {product.store_id}\n"
                    f"Project '{self.project_id.display_name}' belongs to Store: {project_store}\n\n"
                    f"Please ensure all products belong to the same store as the project."
                )
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for product in self.product_ids:
            existing = self.env['mysdb.product_relation'].search([('product_id', '=', product.id)])
            
            if existing:
                if self.replace_existing:
                    existing.write({'project_id': self.project_id.id})
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                self.env['mysdb.product_relation'].create({
                    'product_id': product.id,
                    'project_id': self.project_id.id
                })
                created_count += 1
        
        message = f"Assignment Complete!\n\n"
        message += f"Created: {created_count}\n"
        message += f"Updated: {updated_count}\n"
        message += f"Skipped: {skipped_count}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Assignment Complete',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

class MysdbBulkAssignMarketingWizard(models.TransientModel):
    _name = 'mysdb.bulk.assign.marketing.wizard'
    _description = 'Bulk Assign Products to Marketing Account'

    account_id = fields.Many2one('mysdb.marketing_account', string='Target Marketing Account', required=True,
                                  help="All selected products will be assigned to this marketing account")
    product_ids = fields.Many2many('mysdb.product', string='Products to Assign',
                                     help="Select products to assign to the marketing account")
    store_id = fields.Many2one('mysdb.store', string='Filter by Store',
                                help="Filter products by store for easier selection")
    assignment_filter = fields.Selection([
        ('all', 'All Products'),
        ('unassigned', 'Products Without Marketing'),
        ('incomplete', 'Products Without Complete Assignment')
    ], string='Filter Products', default='unassigned',
       help="Filter which products to show for selection")
    
    preview_count = fields.Integer('Products to Assign', compute='_compute_preview_count')
    
    @api.depends('product_ids')
    def _compute_preview_count(self):
        for wizard in self:
            wizard.preview_count = len(wizard.product_ids)
    
    @api.onchange('store_id', 'assignment_filter')
    def _onchange_filters(self):
        """Update product domain based on filters"""
        domain = []
        
        # Always add store filter if selected
        if self.store_id and self.store_id.store_code:
            domain.append(('store_id', '=', self.store_id.store_code))
        
        # Add assignment filter
        if self.assignment_filter == 'unassigned':
            domain.append(('has_marketing', '=', False))
        elif self.assignment_filter == 'incomplete':
            domain.append(('assignment_status', 'in', ['partial', 'none']))
        # 'all' means no additional assignment filter
        
        # If no filters, ensure we show something (empty domain = all products)
        if not domain:
            domain = [(1, '=', 1)]  # Always true
        
        # Clear selected products when filter changes
        self.product_ids = [(5, 0, 0)]
        
        # Return domain for both the field AND a warning to show domain is active
        result = {'domain': {'product_ids': domain}}
        
        # Add context to help with popup filtering
        if self.store_id or self.assignment_filter != 'all':
            filter_desc = []
            if self.store_id:
                filter_desc.append(f"Store: {self.store_id.display_name}")
            if self.assignment_filter == 'unassigned':
                filter_desc.append("Unassigned products only")
            elif self.assignment_filter == 'incomplete':
                filter_desc.append("Incomplete assignments only")
            
            # Note: This warning won't appear but ensures the onchange is processed
            result['warning'] = {
                'title': 'Filter Applied',
                'message': f"Active filters: {', '.join(filter_desc)}\nNote: Filters apply to product list below. Use search in popup if needed.",
                'type': 'notification'
            }
        
        return result
    
    def action_assign(self):
        """Execute bulk assignment"""
        self.ensure_one()
        
        if not self.product_ids:
            raise ValidationError("Please select at least one product to assign.")
        
        created_count = 0
        skipped_count = 0
        
        for product in self.product_ids:
            # Check if this product-account combination already exists
            existing = self.env['mysdb.product_marketing_relation'].search([
                ('product_id', '=', product.id),
                ('account_id', '=', self.account_id.id)
            ])
            
            if not existing:
                self.env['mysdb.product_marketing_relation'].create({
                    'product_id': product.id,
                    'account_id': self.account_id.id
                })
                created_count += 1
            else:
                skipped_count += 1
        
        message = f"Assignment Complete!\n\n"
        message += f"Created: {created_count}\n"
        message += f"Skipped (already assigned): {skipped_count}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Assignment Complete',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

class MysdbBulkPeriodCreationWizard(models.TransientModel):
    _name = 'mysdb.bulk.period.creation.wizard'
    _description = 'Bulk Period Creation Wizard'
    
    # Step 1: Target Selection
    target_type = fields.Selection([
        ('project', 'Project'),
        ('marketing', 'Marketing Account')
    ], string='Target Type', required=True, default='project')
    
    project_id = fields.Many2one('mysdb.project', string='Project')
    marketing_account_id = fields.Many2one('mysdb.marketing_account', string='Marketing Account')
    
    # Step 2: Period Selection
    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=lambda self: str(datetime.now().year)
    )
    
    create_yearly = fields.Boolean('Create Yearly Period', default=True,
                                   help="Creates period YYYY00 (e.g., 202600)")
    create_monthly = fields.Boolean('Create Monthly Periods', default=True,
                                    help="Creates 12 monthly periods (YYYY01-YYYY12)")
    
    # Optional: Specific months
    select_specific_months = fields.Boolean('Select Specific Months', default=False)
    month_01 = fields.Boolean('January')
    month_02 = fields.Boolean('February')
    month_03 = fields.Boolean('March')
    month_04 = fields.Boolean('April')
    month_05 = fields.Boolean('May')
    month_06 = fields.Boolean('June')
    month_07 = fields.Boolean('July')
    month_08 = fields.Boolean('August')
    month_09 = fields.Boolean('September')
    month_10 = fields.Boolean('October')
    month_11 = fields.Boolean('November')
    month_12 = fields.Boolean('December')
    
    # Step 3: Financial Values
    target_amount = fields.Float('Target Amount', required=True, default=0.0)
    
    cost_calculation_type = fields.Selection([
        ('manual', 'Enter Cost Manually'),
        ('percentage', 'Calculate as % of Target')
    ], string='Cost Calculation', required=True, default='percentage')
    
    cost_percentage = fields.Float('Cost %', default=20.0,
                                   help="Cost as percentage of target (e.g., 20 = 20% of target)")
    cost_amount = fields.Float('Cost Amount', compute='_compute_cost_amount', store=True, readonly=False)
    
    # Distribution
    distribution_type = fields.Selection([
        ('same', 'Same Value for All Periods'),
        ('distribute', 'Distribute Evenly Across Periods')
    ], string='Distribution', default='same', required=True)
    
    # Preview
    preview_count = fields.Integer('Periods to Create', compute='_compute_preview_count')
    preview_text = fields.Text('Preview', compute='_compute_preview_text')
    
    @api.model
    def _get_year_selection(self):
        """Generate year selection from 2024 to current_year + 2"""
        current_year = datetime.now().year
        years = []
        for year in range(2024, current_year + 3):
            years.append((str(year), str(year)))
        return years
    
    @api.depends('cost_calculation_type', 'cost_percentage', 'target_amount')
    def _compute_cost_amount(self):
        for wizard in self:
            if wizard.cost_calculation_type == 'percentage':
                wizard.cost_amount = wizard.target_amount * (wizard.cost_percentage / 100.0)
            # If manual, user enters directly
    
    @api.depends('create_yearly', 'create_monthly', 'select_specific_months',
                 'month_01', 'month_02', 'month_03', 'month_04', 'month_05', 'month_06',
                 'month_07', 'month_08', 'month_09', 'month_10', 'month_11', 'month_12')
    def _compute_preview_count(self):
        for wizard in self:
            count = 0
            if wizard.create_yearly:
                count += 1
            if wizard.create_monthly:
                if wizard.select_specific_months:
                    # Count selected months
                    for month in range(1, 13):
                        if getattr(wizard, f'month_{month:02d}'):
                            count += 1
                else:
                    count += 12
            wizard.preview_count = count
    
    @api.depends('year', 'target_type', 'project_id', 'marketing_account_id',
                 'target_amount', 'cost_amount', 'preview_count', 'distribution_type')
    def _compute_preview_text(self):
        for wizard in self:
            lines = []
            
            # Target info
            if wizard.target_type == 'project' and wizard.project_id:
                target_name = wizard.project_id.display_name
            elif wizard.target_type == 'marketing' and wizard.marketing_account_id:
                target_name = wizard.marketing_account_id.display_name
            else:
                target_name = "Not selected"
            
            lines.append(f"For: {target_name}")
            lines.append(f"Year: {wizard.year}")
            lines.append("")
            
            # Calculate per-period values
            if wizard.distribution_type == 'distribute' and wizard.preview_count > 0:
                per_period_target = wizard.target_amount / wizard.preview_count
                per_period_cost = wizard.cost_amount / wizard.preview_count
            else:
                per_period_target = wizard.target_amount
                per_period_cost = wizard.cost_amount
            
            lines.append(f"Will create {wizard.preview_count} period record(s):")
            lines.append("")
            
            # Show examples
            if wizard.create_yearly:
                lines.append(f"• {wizard.year}-00 (Yearly): Target {per_period_target:,.2f} | Cost {per_period_cost:,.2f}")
            
            if wizard.create_monthly:
                if wizard.select_specific_months:
                    shown = 0
                    for month in range(1, 13):
                        if getattr(wizard, f'month_{month:02d}') and shown < 3:
                            month_name = calendar.month_abbr[month]
                            lines.append(f"• {wizard.year}-{month:02d} ({month_name}): Target {per_period_target:,.2f} | Cost {per_period_cost:,.2f}")
                            shown += 1
                    if wizard.preview_count > shown + (1 if wizard.create_yearly else 0):
                        remaining = wizard.preview_count - shown - (1 if wizard.create_yearly else 0)
                        lines.append(f"  ... and {remaining} more month(s)")
                else:
                    lines.append(f"• {wizard.year}-01 (Jan): Target {per_period_target:,.2f} | Cost {per_period_cost:,.2f}")
                    lines.append(f"• {wizard.year}-02 (Feb): Target {per_period_target:,.2f} | Cost {per_period_cost:,.2f}")
                    if wizard.preview_count > 3:
                        lines.append(f"  ... and {wizard.preview_count - 2 - (1 if wizard.create_yearly else 0)} more month(s)")
            
            wizard.preview_text = "\n".join(lines)
    
    @api.onchange('target_type')
    def _onchange_target_type(self):
        """Clear selection when type changes"""
        if self.target_type == 'project':
            self.marketing_account_id = False
        else:
            self.project_id = False
    
    @api.onchange('create_monthly', 'select_specific_months')
    def _onchange_monthly_selection(self):
        """Enable/disable specific month selection"""
        if not self.create_monthly:
            self.select_specific_months = False
    
    def action_create_periods(self):
        """Create all periods based on wizard configuration"""
        self.ensure_one()
        
        # Validate
        if self.target_type == 'project' and not self.project_id:
            raise ValidationError("Please select a Project")
        if self.target_type == 'marketing' and not self.marketing_account_id:
            raise ValidationError("Please select a Marketing Account")
        
        if not self.create_yearly and not self.create_monthly:
            raise ValidationError("Please select at least one option: Yearly or Monthly periods")
        
        if self.target_amount <= 0:
            raise ValidationError("Target amount must be greater than zero")
        
        # Determine target object
        if self.target_type == 'project':
            target_object = f'mysdb.project,{self.project_id.id}'
        else:
            target_object = f'mysdb.marketing_account,{self.marketing_account_id.id}'
        
        # Calculate per-period values
        periods_to_create = []
        
        if self.create_yearly:
            periods_to_create.append(f"{self.year}00")
        
        if self.create_monthly:
            if self.select_specific_months:
                for month in range(1, 13):
                    if getattr(self, f'month_{month:02d}'):
                        periods_to_create.append(f"{self.year}{month:02d}")
            else:
                for month in range(1, 13):
                    periods_to_create.append(f"{self.year}{month:02d}")
        
        # Calculate amounts
        if self.distribution_type == 'distribute':
            per_period_target = self.target_amount / len(periods_to_create)
            per_period_cost = self.cost_amount / len(periods_to_create)
        else:
            per_period_target = self.target_amount
            per_period_cost = self.cost_amount
        
        # Create periods
        created_count = 0
        skipped_count = 0
        
        PeriodModel = self.env['mysdb.period_target_cost']
        
        for period in periods_to_create:
            # Check if period already exists
            existing = PeriodModel.search([
                ('period', '=', period),
                ('target_object', '=', target_object)
            ])
            
            if existing:
                skipped_count += 1
                continue
            
            # Create new period
            PeriodModel.create({
                'period': period,
                'target_object': target_object,
                'target': per_period_target,
                'cost': per_period_cost
            })
            created_count += 1
        
        # Return notification
        message = f"Period Creation Complete!\n\n"
        message += f"Created: {created_count} period(s)\n"
        if skipped_count > 0:
            message += f"Skipped: {skipped_count} (already exist)\n"
        message += f"\nTarget per period: {per_period_target:,.2f}\n"
        message += f"Cost per period: {per_period_cost:,.2f}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }
