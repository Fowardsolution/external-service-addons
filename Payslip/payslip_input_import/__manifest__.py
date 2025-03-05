# -*- coding: utf-8 -*-
{
    'name': "Payslip Input Import",

    'summary': """Import data for payslip inputs""",

    'description': """

    """,

    'author': "Foward Solution SRL",
    'website': 'http://Fowardsolution.com.do',
    'category': 'Extra Tools',
    'version': '17.0.1.0',
    'depends': ['base_setup','hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/payroll_structure.xml',
        'data/salary_rule_categories.xml',        
        'data/nomina_regular.xml',
        'views/views.xml',
        'views/inherit_hr_payslip.xml',
        'views/inherit_hr_payslip_run.xml',
    ],
}
