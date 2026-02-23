# -*- coding: utf-8 -*-
{
    'name': "My SDB Reporting",
    'version': '17.0.1.0.0',
    'category': 'Reporting',
    'summary': "My SDB reporting and analytics.",
    'description': "Reporting tools for My SDB data.",
    'author': 'My SDB',
    'company': 'My SDB',
    'maintainer': 'My SDB',
    'website': '',
    'depends': ['base', 'spreadsheet', 'board'],
    'data': [
        'security/security_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/mysdb_data_views.xml',
        'views/mysdb_enhanced_views.xml',
        'views/mysdb_credential_views.xml',
        'views/mysdb_api_views.xml',
        'views/mysdb_connector_views.xml',
        'views/mysdb_sheet_views.xml',
        'views/mysdb_menus.xml',
    ],
    'external_dependencies': {
        'python': ['mysql-connector-python', 'cryptography', 'google-auth', 'google-auth-httplib2', 'google-api-python-client']
        },
    'images': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_init_hook': 'post_init_hook',
}
