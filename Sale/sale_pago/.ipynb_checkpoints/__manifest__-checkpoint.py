# Copyright 2022 - ISIAS MATEO
{
    "name": "IBRISSA - PAGOS",
    "summary": "Add some useful features",
    "version": "13.0.1.0.0",
    "category": "Extra",
    'author': 'ISIAS MATEO <isias1626@gmail.com>',
    'external_dependencies': {
        'python': [
            'pandas',
        ],
    },
    "depends": [
        "account",
        "sale",
    ],
    "data": [
        "views/sale_view.xml",
        "views/payment_view.xml",
    ],
    "application": True,
    'installable': True,
}
