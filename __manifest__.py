# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Marketplace',
    'version': '1.0',
    'category': 'Customization',
    'summary': 'Marketplace API Integration',
    'description': """

MarketPlace API Integration
===============================
TASK ID - 2711537
    """,
    'depends': [
        'crm',
        'delivery',
        'mrp',
        'sale_management',
        'website',
        'meta_SO_status_field',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/marketplace_config_details_view.xml',
        'views/marketplace_product_category_view.xml',
        'views/product_template_view.xml',
        'views/sale_order_view.xml',
        'views/marketplace_product_brand_view.xml',
        'views/res_partner_view.xml',
        'views/marketplace_models_view.xml',
        'views/stock_warehouse_view.xml',
        'wizard/marketplace_config_wizard_view.xml',
        'views/themarket_color_mapping_view.xml', #niaj
    ],
    'demo':[],
    'application': True,
    'installable': True,
    'auto_install': False,
}
