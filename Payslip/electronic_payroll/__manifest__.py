# -*- coding: utf-8 -*-
{
    'name': "Electronic Payroll",

    'summary': """
        Genera archivo TXT de la nomina electronica""",

    'description': """
 Genera la nomina electronica para diferentes banco de la Rep. Dominicana.
    """,

    'author': "Foward Solution SRL",
    'website': 'http://Fowardsolution.com.do', 
    'category': 'Uncategorized',
    'version': '17.0.1.0',
    'depends': ['base', 'hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/res_bank.xml',
        'views/ir_config_settings.xml',
        'data/res.bank.csv',
        'data/sequence.xml',
    ],

}
