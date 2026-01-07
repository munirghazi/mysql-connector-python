# -*- coding: utf-8 -*-
from odoo import models, fields

class MysqlOrder(models.Model):
    _name = 'mysql.order'
    _description = 'MySQL Orders'
    _rec_name = 'order_code'

    order_id = fields.Char('Order ID', required=True, index=True) # Added index
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
    transaction_reference = fields.Char('Transaction Ref')
    transaction_amount = fields.Float('Transaction Amount')
    transaction_amount_string = fields.Char('Transaction Amount String')
    issue_date = fields.Char('Issue Date')
    payment_status = fields.Char('Payment Status', index=True)
    is_potential_fraud = fields.Boolean('Potential Fraud')
    source = fields.Char('Source')
    source_code = fields.Char('Source Code')
    payment_method_name = fields.Char('Payment Method')
    payment_method_code = fields.Char('Payment Code')
    payment_method_type = fields.Char('Payment Type')
    order_created_at = fields.Datetime('Order Created At', index=True)
    order_updated_at = fields.Char('Order Updated At (MySQL String)')
    mysql_created_at = fields.Datetime('Sync Created At')
    mysql_updated_at = fields.Datetime('Sync Updated At')

class MysqlOrderDetail(models.Model):
    _name = 'mysql.order.detail'
    _description = 'MySQL Order Details'

    order_linked_id = fields.Char('Order Linked ID', index=True) # Added index
    store_id = fields.Char('Store ID')
    currency_code = fields.Char('Currency')
    product_name = fields.Char('Product Name', index=True)
    product_sku = fields.Char('SKU', index=True)
    total = fields.Float('Total')
    invoice_link = fields.Char('Invoice Link')
    order_detail_uuid = fields.Char('Detail UUID')
    mysql_created_at = fields.Datetime('Created At')
    mysql_updated_at = fields.Datetime('Updated At')

class MysqlProduct(models.Model):
    _name = 'mysql.product'
    _description = 'MySQL Products'
    _rec_name = 'product_name'

    store_id = fields.Char('Store ID')
    product_id = fields.Char('Product ID', required=True, index=True)
    product_sku = fields.Char('SKU')
    product_name = fields.Char('Product Name', required=True)
    product_slug = fields.Char('Slug')
    product_short_description = fields.Text('Short Description')
    product_price = fields.Float('Price')
    image_url = fields.Text('Image URL')
    product_quantity = fields.Float('Quantity')
    product_currency = fields.Char('Currency')
    product_currency_symbol = fields.Char('Currency Symbol')
    html_url = fields.Char('HTML URL')
    mysql_created_at = fields.Datetime('Created At')
    mysql_updated_at = fields.Datetime('Updated At')

class MysqlProject(models.Model):
    _name = 'mysql.project'
    _description = 'MySQL Projects'
    _rec_name = 'project_name_en'

    store_id = fields.Char('Store ID')
    project_name_ar = fields.Char('Name (AR)')
    project_name_en = fields.Char('Name (EN)')
    project_starting_period = fields.Char('Start Period')
    project_ending_period = fields.Char('End Period')
    project_year = fields.Char('Year')
    mysql_created_at = fields.Datetime('Created At')
    mysql_updated_at = fields.Datetime('Updated At')

class MysqlPos(models.Model):
    _name = 'mysql.pos'
    _description = 'MySQL Point of Sales'
    _rec_name = 'pos_name_en'

    pos_name_ar = fields.Char('POS Name (AR)')
    pos_name_en = fields.Char('POS Name (EN)')
    pos_name_sales_person = fields.Char('Sales Person')
    project_id = fields.Char('Project ID')
    section_id = fields.Char('Section ID')
    pos_name_sales_person_phone_no = fields.Char('Sales Person Phone')
    pos_name_sales_person_zid_id = fields.Char('Sales Person Zid ID')
    product_id = fields.Char('Product ID', index=True)
    mysql_created_at = fields.Datetime('Created At')
    mysql_updated_at = fields.Datetime('Updated At')

class MysqlOrderReport(models.Model):
    _name = 'mysql.order.report'
    _description = 'MySQL Combined Order Analysis'
    _auto = False

    order_code = fields.Char('Order Code', readonly=True)
    customer_name = fields.Char('Customer', readonly=True)
    store_name = fields.Char('Store', readonly=True)
    payment_status = fields.Char('Status', readonly=True)
    product_name = fields.Char('Product', readonly=True)
    product_sku = fields.Char('SKU', readonly=True)
    product_slug = fields.Char('Product Slug', readonly=True)
    line_total = fields.Float('Line Total', readonly=True)
    order_total = fields.Float('Order Total', readonly=True)
    order_created_at = fields.Datetime('Order Created At', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS mysql_order_report")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mysql_order_report AS (
                SELECT 
                    d.id as id,
                    COALESCE(o.order_code, 'N/A') as order_code,
                    COALESCE(o.customer_name, 'Unknown') as customer_name,
                    COALESCE(o.store_name, 'Unknown') as store_name,
                    COALESCE(o.payment_status, 'Unknown') as payment_status,
                    COALESCE(d.product_name, 'No Product') as product_name,
                    d.product_sku as product_sku,
                    p.product_slug as product_slug,
                    COALESCE(d.total, 0.0) as line_total,
                    COALESCE(o.order_total, 0.0) as order_total,
                    CAST(o.order_created_at AS TIMESTAMP) as order_created_at
                FROM mysql_order_detail d
                LEFT JOIN mysql_order o ON d.order_linked_id = o.order_id
                LEFT JOIN mysql_product p ON (d.product_sku = p.product_sku AND d.store_id = p.store_id)
            )
        """)
