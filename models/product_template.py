# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from copy import copy
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# fields and method to use api call
MARKETPLACE_HOOK_FIELDS = {
    'trade_me_listing_rule_ids': '_trade_me_listing_rule',
}

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    marketplace_config_ids = fields.One2many('marketplace.product.template', 'product_template_id', string="Marketplace Application", copy=False)
    marketplace_brand_id = fields.Many2one('marketplace.product.brand', string='Trademe Brand', domain=[('config_id.api_provider', '=', 'tradevine')])
    themarket_brand_id = fields.Many2one('marketplace.product.brand', string='TheMarket Brand',  domain=[('config_id.api_provider', '=', 'themarket')])
    themarket_category_id = fields.Many2one('marketplace.product.category', string='TheMarket Category',  domain=[('marketplace_config_id.api_provider', '=', 'themarket')])
    is_manual_order_approval_needed = fields.Boolean(copy=False, help='''
        This is a product level flag which indicates that sales orders that contain this product
        should require manual approval before transitioning from Pending to Awaiting Shipment''')
    marketplace_enable_inventory = fields.Boolean(copy=False, default=True, help='''Whether this product is inventory-tracked or not i.e. true or false''')
    marketplace_photo_id = fields.Char('TradeVine PhotoID', copy=False)
    photo_identifier = fields.Char('Marketplace Photo Identifier', copy=False)
    marketplace_inventory_adjustment_ids = fields.One2many('marketplace.inventory.adjustment.history', 'product_template_id', string="Inventory Adjustment History", copy=False)
    trade_me_listing_rule_ids = fields.One2many('trade.me.listing.rule', 'product_template_id', string='TradeMe Listing Rule')
    themarket_listing_rule_ids = fields.One2many('themarket.listing.rule', 'product_template_id', string='TheMarket Listing Rule')

    @api.model_create_multi
    def create(self, vals_list):
        templates = super(ProductTemplate, self).create(vals_list)
        for template in templates:
            for config in template.product_variant_id.marketplace_config_ids:
                config.write({'product_template_id': template.id})
        return templates

    def action_post_product_data_on_marketpalce(self):
        marketplace_config_ids = self.env['marketplace.config.details'].search([],limit=1)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.config.wizard',
            'view_mode': 'from',
            'views': [[self.env.ref('marketplace_connector.view_marketplace_config_wizard_form').id, 'form']],
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_ids': self.ids,
                'default_marketplace_config_ids':[(4,marketplace_config_ids.id)],
                'method': 'product'
            },
            'name': _('Create/Update Product for Marketplace Account'),
        }

    @api.depends("virtual_available")
    def _trigger_update_stock_on_free_qty_change(self):
        _logger.warning('>>>>>>_trigger_update_stock_on_free_qty_change for product template ids {}'.format(self.ids))
        for product in self.mapped('product_variant_ids'):
            product._call_to_update_marketplace_product_stock()

            
class ProductProduct(models.Model):
    _inherit = 'product.product'

    # stock_free_qty = fields.Float(string="Stock Free Qty", store=True, help='Technical: used to monitor current stock quantities.')
    marketplace_config_ids = fields.One2many('marketplace.product.template', 'product_id', string="Marketplace Application", copy=False)
    marketplace_inventory_adjustment_ids = fields.One2many('marketplace.inventory.adjustment.history', 'product_id', string="Inventory Adjustment History", copy=False)
    themarket_sku_ref = fields.Integer(string = "The Market SKU Ref ID",required=False)

    def action_post_product_data_on_marketpalce(self):
        marketplace_config_ids = self.env['marketplace.config.details'].search([],limit=1)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.config.wizard',
            'view_mode': 'from',
            'views': [[self.env.ref('marketplace_connector.view_marketplace_config_wizard_form').id, 'form']],
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_ids': self.ids,
                'default_marketplace_config_ids':[(4,marketplace_config_ids.id)],
                'method': 'product'
            },
            'name': _('Create/Update Product for Marketplace Account'),
        }

    # ####___OVERRIDE_______#########
    # @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
    # @api.depends_context(
    #     'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
    #     'location', 'warehouse',
    # )
    # def _compute_quantities(self):
    #     products = self.filtered(lambda p: p.type != 'service')
    #     res = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
    #     for product in products:
    #         product.qty_available = res[product.id]['qty_available']
    #         product.incoming_qty = res[product.id]['incoming_qty']
    #         product.outgoing_qty = res[product.id]['outgoing_qty']
    #         product.virtual_available = res[product.id]['virtual_available']
    #         product.free_qty = res[product.id]['free_qty']
    #         product.stock_free_qty = res[product.id]['free_qty']
    #         if product.default_code == 'TEST1243':
    #             _logger.warning('_call_to_compute_quantities for product variant id {} stock_free_qty {}'.format(product.id, product.stock_free_qty))

            
    #     # Services need to be set with 0.0 for all quantities
    #     services = self - products
    #     services.qty_available = 0.0
    #     services.incoming_qty = 0.0
    #     services.outgoing_qty = 0.0
    #     services.virtual_available = 0.0
    #     services.free_qty = 0.0
    #     services.stock_free_qty = 0.0
     

    @api.depends("virtual_available")
    def _trigger_update_stock_on_free_qty_change(self):
        _logger.warning('>>>>>>_trigger_update_stock_on_free_qty_change for product variant ids {}'.format(self.ids))
        for product in self.filtered(lambda p: p.marketplace_config_ids):
            product._call_to_update_marketplace_product_stock()


    
    def _call_to_update_marketplace_product_stock(self, sale_order=None):
        _logger.warning('_call_to_update_marketplace_product_stock for product variant id {}'.format(self.ids))
        for config in self.mapped('marketplace_config_ids.config_id'):
            api_provider = config.api_provider
            location_ids = config.location_ids or False
            _logger.warning('##### marketplace stock update api_provider {} and location_ids {}'.format(api_provider, location_ids.ids))

            api_provider_obj = self.env['%s' % api_provider]
            if hasattr(api_provider_obj, '_update_%s_product_stock' % api_provider):
                for product in self.filtered(lambda product: config.id in product.marketplace_config_ids.mapped('config_id').ids):
                    _logger.warning('##### marketplace stock update product {}'.format(product.name))

                    result = getattr(api_provider_obj, '_update_%s_product_stock' % api_provider)(config, product, location_ids, sale_order)
                    msg = result.get('error_message')
                    if isinstance(result, dict) and not result.get('error_message'):
                        msg = _('Successfully Update products stock for %s account!' % api_provider)
                        _logger.warning('{}'.format(msg))
                    else:
                        _logger.error('{}'.format(msg))
        return True
