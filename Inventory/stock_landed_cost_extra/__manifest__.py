# -*- coding: utf-8 -*-
{
    'name': "Stock Landed Cost Extra",

    'summary': """
    
    """,

    'description': """
    """,

    'author': "Foward Solution SRL",
    'website': "",

    'category': 'Uncategorized',
    'version': '17.0.1.0.0',

    'depends': ['base', 'account', 'purchase', 'stock', 'stock_landed_costs', 'report_xlsx_helper'],

    'data': [
        'wizard/wizard.xml',
        'views/views.xml',
        'views/templates.xml',
        #'views/stock_view.xml',
        'views/product_view.xml',
        'views/account_view.xml',
        'views/purchase_view.xml',
        'security/ir.model.access.csv'
    ],
}
