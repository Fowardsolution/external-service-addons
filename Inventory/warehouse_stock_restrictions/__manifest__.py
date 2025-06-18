# -*- coding: utf-8 -*-
{
    'name': "Warehouse Restrictions",

    'summary': """
         Restricción de ubicación de almacén y stock para usuarios.""",

    'description': """
        Este módulo restringe al usuario el acceso al almacén y al proceso de movimientos de stock distintos a los permitidos para los almacenes y las ubicaciones de stock.
    """,

    'author': "Foward Solution SRL",
    'website': "http://www.fowardsolution.com.do",
    'license':'OPL-1',	
    'category': 'Warehouse',
    'version': '17.0.1.0.0',
    'depends': ['base', 'stock'],

    'data': [

        'views/users_view.xml',
        'security/security.xml',
        # 'security/ir.model.access.csv',
    ],
    
    
}
