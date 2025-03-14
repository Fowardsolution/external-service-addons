# -*- coding: utf-8 -*-
{
    'name': "l10n_do_sequence_inherit",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "isias1626@gmail.com",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '15.0.0.0.2',
    'depends': ['base', 'account', 'l10n_do_accounting', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
}
