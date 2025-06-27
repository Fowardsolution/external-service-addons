# -*- coding: utf-8 -*-
{
    'name': "creator_firms",
    'summary': """
    Create signs in reports""",
    'description': """
        Create firms in the all reports.
    """,
    'author': "isias1626@gmail.com",
    'category': 'Application',
    'version': '15.0.1.0.1',
    'depends': ['base', 'report_qweb_element_page_visibility'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
}
