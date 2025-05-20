# Copyright 2023 - ISIAS MATEO
{
    "name": "SALE - PAGOS",
    "summary": "Add some useful features",
    "version": "17.0.0.0.1",
    "category": "Extra",
    'author': 'ISIAS MATEO <isias1626@gmail.com>, Jean Carlos Rodriguez <jrodriguez@fowardsolution.com.do>',
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
