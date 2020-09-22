# Copyright 2020 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Br Delivery',
    'summary': """
        Implements Brazilian freight values for delivery.""",
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'KMEE,Odoo Community Association (OCA)',
    'website': 'www.kmee.com.br',
    'depends': [
        'delivery',
        'website_sale_delivery',
        'website_sale',
    ],
    'data': [
        'views/website_sale_delivery_templates.xml'
    ],
    'demo': [
    ],
}
