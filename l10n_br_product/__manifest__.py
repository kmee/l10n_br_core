# -*- coding: utf-8 -*-
# Copyright 2018 Odoo Community Association
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Br Product',
    'summary': """
        Cadastro de produtos Brasileiro""",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Odoo Community Association (OCA)',
    'depends': [
        'l10n_br_base',
        'product',
    ],
    'data': [
        'views/menu.xml',
        'views/product_view.xml',
    ],
    'demo': [
    ],
}
