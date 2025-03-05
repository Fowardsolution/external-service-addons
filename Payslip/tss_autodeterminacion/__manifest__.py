# -*- coding: utf-8 -*-
{
    'name': "TSS - Autodeterminacion",

    'summary': """Genera el reporte de Autodeterminacion de la TSS.""",

    'description': """
    
     """,

    'author': "Foward Solution SRL",
    'website': 'http://Fowardsolution.com.do',
    'category': 'Uncategorized',
    'version': '17.0.1.0',
    'depends': ['base', 'hr_payroll'],

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/inherit_salary_rule.xml',
        'data/data.xml',
        'views/inherit_hr_employee.xml',
        'views/res_company_view.xml',
    ],
}