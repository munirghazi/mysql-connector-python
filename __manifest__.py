# -*- coding: utf-8 -*-
{
    'name': "Odoo MySDB Connector",
    'version': '17.0.2.0.0',
    'category': 'Extra Tools',
    'summary': """Enhanced MySDB Connector with Project & Marketing Income Analysis, 
     Data Quality Audit, and Bulk Assignment Tools.""",
    'description': """This enhanced module provides comprehensive business intelligence 
     for MySDB data including: Project & Marketing Income Reports with ROI/Profit tracking, 
     Period-based Target Achievement Analysis, Automated Data Quality Audits, 
     Bulk Product Assignment Wizards, and seamless data import from MySDB databases.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'spreadsheet', 'board'],
    'data': [
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'data/ir_cron_data.xml',
        'views/mysdb_data_views.xml',
        'views/mysdb_enhanced_views.xml',
        'views/mysdb_credential_views.xml',
        'views/mysdb_connector_views.xml',
        'views/mysdb_menus.xml',
    ],
    'external_dependencies': {
        'python': ['mysql-connector-python', 'cryptography']
        },
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
