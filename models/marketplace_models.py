# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from copy import copy
from email.policy import default
from multiprocessing import Condition
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ...marketplace_connector.models import tradevine_lookup
from ...marketplace_connector.models import kogan_lookup

import logging
_logger = logging.getLogger(__name__)


class MarketPlace(models.Model):
    _name = 'marketplace.marketplace'
    _description = 'Marketplace'

    name = fields.Char(required=True)
    config_id = fields.Many2one('marketplace.config.details', string='Marketplace Application', required=True, ondelete='cascade')
    ref_code = fields.Char('Ref.Code', required=True)


class MarketPlacePartner(models.Model):
    _name = 'marketplace.res.partner'
    _inherit = 'marketplace.marketplace'
    _description = 'Marketplace Partner'

    partner_id = fields.Many2one('res.partner', string='Customer')
    default_billing_address_id = fields.Char('Billing Address', copy=False)
    default_shipping_address_id = fields.Char('Shipping Address', copy=False)





class MarketPlaceProductTemplate(models.Model):
    _name = 'marketplace.product.template'
    _inherit = 'marketplace.marketplace'
    _description = 'Marketplace Product Template'
    _rec_name = 'product_id'
    
    product_template_id = fields.Many2one('product.template', ondelete='cascade')
    product_id = fields.Many2one('product.product', ondelete='cascade')
    category_ref_id = fields.Char(copy=False)
    product_template_qty = fields.Float('virtual_available')
    product_qty = fields.Float('free_qty')

    _sql_constraints = [
        ('ref_code', 'unique (ref_code)', 'product ref code must be unique!')
    ]

    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        self.name = self.product_template_id.name
        
        
        
class ProductCreationDetails(models.Model):
    _name = 'product.create.detail'
    _description = 'Marketplace Product Creation Details'
    
    name = fields.Char()
    config_id = fields.Many2one('marketplace.config.details', string='Marketplace Application', ondelete='cascade')
    kogan_async_link = fields.Char(string="Kogan Pending URL")
    request_data = fields.Char(string="JSON Data")
    checked = fields.Boolean(String="Checked")
    status = fields.Selection([('draft', 'Draft'), ('complete', 'Complete'), ('failed', 'Failed'), ('complete_with_error', 'Complete with Error')])




class MarketPlaceOrder(models.Model):
    _name = 'marketplace.order'
    _inherit = 'marketplace.marketplace'
    _description = 'Marketplace Order'

    sale_order_ref = fields.Char(copy=False)

    _sql_constraints = [
        ('ref_code', 'unique (ref_code)', 'product ref code must be unique!')
    ]

class MarketPlaceOrderLine(models.Model):
    _name = 'marketplace.order.line'
    _inherit = 'marketplace.marketplace'
    _description = 'Marketplace Order Line'

    _sql_constraints = [
        ('ref_code', 'unique (ref_code)', 'product ref code must be unique!')
    ]

class MarketPlaceProductCategory(models.Model):
    _name = 'marketplace.product.category'
    _description = 'Marketplace Product Category'
    # _parent_name = "parent_id"
    # _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(required=True, index=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    marketplace_catg_ref_number = fields.Char(string='Category Number', readonly=True, required=True)
    marketplace_path = fields.Char()
    marketplace_config_id = fields.Many2one('marketplace.config.details', required=True)
    parent_id = fields.Many2one(
        'marketplace.product.category', string='Parent', index=True, 
        domain="[('marketplace_config_id', '=', marketplace_config_id)]",
        ondelete='cascade'
    ) 
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('marketplace.product.category', 'parent_id', 'Child Categories')
    active = fields.Boolean(default=True)
    product_count = fields.Integer(
        '# Products', compute='_compute_product_count',
        help="The number of products under this category (Does not consider the children categories)")


    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_("Error! You cannot create recursive hierarchy of marketplace product category"))
        return True

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _compute_product_count(self):
        read_group_res = self.env['product.template'].read_group([('categ_id', 'child_of', self.ids)], ['categ_id'], ['categ_id'])
        group_data = dict((data['categ_id'][0], data['categ_id_count']) for data in read_group_res)
        for categ in self:
            product_count = 0
            for sub_categ_id in categ.search([('id', 'child_of', categ.ids)]).ids:
                product_count += group_data.get(sub_categ_id, 0)
            categ.product_count = product_count

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]






class MarketplaceProductBrand(models.Model):
    _name = 'marketplace.product.brand'
    _description = 'Prodcut Brand'
    _inherit = ['image.mixin']

    name = fields.Char(required=True)
    config_id = fields.Many2one('marketplace.config.details', string='Marketplace Application', required=True, ondelete='cascade')
    description = fields.Text(string='Product Description')
    ref_code = fields.Char(string="Marketplace Brand ID")


class MarketplaceInventoryAdjustmentHistory(models.Model):
    _name = 'marketplace.inventory.adjustment.history'
    _inherit = 'marketplace.marketplace'
    _description = 'Inventory Adjustment History'

    product_template_id = fields.Many2one('product.template', ondelete='cascade')
    product_id = fields.Many2one('product.product', ondelete='cascade')

class MarketplaceStockWarehouse(models.Model):
    _name = 'marketplace.stock.warehouse'
    _inherit = 'marketplace.marketplace'
    _description = 'Marketplace stock warehouse'

    warehouse_id = fields.Many2one('stock.warehouse', ondelete='cascade')










# TradeVine >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
class TradeMeListingRule(models.Model):
    _name = 'trade.me.listing.rule'
    _description = 'Trademe Linsting Rule'


    LISTING_RULE = [(str(k), v) for k, v in tradevine_lookup.get_trade_me_listing_rule_priority().items()]
   
    name = fields.Char(required=True, index=True, default='Rule_MM')
    config_id = fields.Many2one('marketplace.config.details', string='Marketplace Application', domain=[('api_provider', '=', 'tradevine')], required=True, ondelete='cascade')
    ref_code = fields.Char()
    product_template_id = fields.Many2one('product.template', ondelete='cascade')
    product_id = fields.Many2one('product.product', ondelete='cascade')
    marketplace_product = fields.Many2one('marketplace.product.template', compute='_compute_marketplace_product', domain=[('config_id.api_provider', '=', 'tradevine')], readonly=True, store=True)
    is_auto_listing_enabled = fields.Boolean(string='Auto-listing',default=True)
    is_use_buy_now_enabled = fields.Boolean(string='Buy Now Only', default=True)
    buy_now_max_qty = fields.Float(string='Maximum Quantity', readonly=False, store=True)
    auto_listing_priority = fields.Selection(LISTING_RULE, required=True, default="73002")
    title = fields.Char(required=True, related='product_template_id.name', readonly=False)
    subtitle = fields.Char(string= "Subtitle", compute='_compute_subtitle', copy=False, readonly=False)
    start_price = fields.Float('Start Price', related='product_template_id.list_price', readonly=False)
    buy_now_price = fields.Float('Buy Now Price',related='product_template_id.list_price', readonly=False)
    external_trade_me_organisation_name = fields.Char(related='config_id.external_trade_me_organisation_name')
    productID = fields.Char()
    category_number = fields.Many2one('marketplace.product.category', required=True)
    description = fields.Text(related='product_template_id.description_sale', string="Description")
    brand = fields.Many2one('marketplace.product.brand', string='Marketplace Brand', related='product_template_id.marketplace_brand_id', readonly=False)
    is_listing_new = fields.Boolean(string='Brand new', default=True,
    help="Uncheck this box if this product is Used condition.")


    def _compute_subtitle(self):
        if not self.subtitle:
            if self.product_template_id.marketplace_brand_id:
                self.subtitle = "Original " + self.product_template_id.marketplace_brand_id.name + " Brand Product"
            else:
                self.subtitle = "Original Brand Product"


    @api.constrains('start_price', 'buy_now_price')
    def _check_listing_price(self):
        for rule in self:
            if not rule.is_use_buy_now_enabled and rule.start_price > rule.buy_now_price:
                raise ValidationError(_("Error! For Listing Rule, The Buy Now price cannot be less than the Start price."))
            if not rule.is_use_buy_now_enabled and rule.start_price == 0:
                raise ValidationError(_("Error! StartPrice must be greater than zero."))
        return True

    @api.depends('product_id.marketplace_config_ids.ref_code', 'product_template_id.marketplace_config_ids.ref_code')
    def _compute_marketplace_product(self):
        for rule in self:
            if rule.product_id:
                product_id = rule.product_id.marketplace_config_ids.filtered(lambda rec: rec.product_id == rule.product_id)
                if len(product_id) > 0:
                    rule.marketplace_product = product_id[0]
                    break
            if rule.product_template_id:
                product_template_id = rule.product_template_id.marketplace_config_ids.filtered(lambda rec: rec.product_id == rule.product_template_id)
                if len(product_template_id) > 0:
                    rule.marketplace_product = product_template_id[0]
                    break
            rule.marketplace_product = False

    def unlink(self):
        for rule in self.exists():
            if rule.ref_code:
                api_provider = rule.config_id.api_provider
                api_provider_obj = self.env['%s' % api_provider]
                api_provider_obj._delete_tradevine_listing_rule(rule)
        return super(TradeMeListingRule, self).unlink()











#Kogan >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
class KoganListingRule(models.Model):
    _name = 'kogan.listing.rule'
    _description = 'Kogan Linsting Rule'


    LISTING_RULE = [(str(k), v) for k, v in kogan_lookup.get_kogan_listing_rule_priority().items()]
    name = fields.Char(required=True, index=True, default='Rule_MM_Kogan')
    config_id = fields.Many2one('marketplace.config.details', string='Marketplace Application', domain=[('api_provider', '=', 'kogan')], required=True, ondelete='cascade')
    ref_code = fields.Char("Kogan Style Id", copy=False)
    product_template_id = fields.Many2one('product.template', ondelete='cascade')
    product_id = fields.Many2one('product.product', ondelete='cascade')
    marketplace_product = fields.Many2one('marketplace.product.template', compute='_compute_marketplace_product', domain=[('config_id.api_provider', '=', 'kogan')], readonly=True, store=True)
    is_auto_listing_enabled = fields.Boolean(string='Auto-listing',default=True)
    is_use_buy_now_enabled = fields.Boolean(string='Buy Now Only', default=True)
    buy_now_max_qty = fields.Float(string='Maximum Quantity', readonly=False, store=True)
    auto_listing_priority = fields.Selection(LISTING_RULE, required=True, default="73002")
    title = fields.Char(required=True, related='product_template_id.name', readonly=False)
    subtitle = fields.Char(string= "Subtitle", compute='_compute_subtitle', copy=False, readonly=False)
    start_price = fields.Float('Start Price', related='product_template_id.list_price', readonly=False)
    buy_now_price = fields.Float('Buy Now Price',related='product_template_id.list_price', readonly=False)
    # Issue : external_trade_me_organisation_name  marketplace_config_details.py ( Line 39 )
    # external_kogan_organisation_name = fields.Char(related='config_id.external_trade_me_organisation_name')

    productID = fields.Char()
    description = fields.Text(related='product_template_id.description_sale', string="Description")
    brand = fields.Many2one('marketplace.product.brand', string='Marketplace Brand', related='product_template_id.marketplace_brand_id',domain=[('config_id.api_provider', '=', 'kogan')], readonly=False)
    category_number = fields.Many2one('marketplace.product.category',string='Kogan Category', required=True)
    is_listing_new = fields.Boolean(string='Brand new', default=True, help="Uncheck this box if this product is Used condition.")


    def _compute_subtitle(self):
        if not self.subtitle:
            # pass    
            if self.product_template_id.kogan_brand_id:
                self.subtitle = "Original " + self.product_template_id.kogan_brand_id.name + " Brand Product"
            else:
                self.subtitle = "Original Brand Product"


    @api.constrains('start_price', 'buy_now_price')
    def _check_listing_price(self):
        for rule in self:
            if not rule.is_use_buy_now_enabled and rule.start_price > rule.buy_now_price:
                raise ValidationError(_("Error! For Listing Rule, The Buy Now price cannot be less than the Start price."))
            if not rule.is_use_buy_now_enabled and rule.start_price == 0:
                raise ValidationError(_("Error! StartPrice must be greater than zero."))
        return True

    @api.depends('product_id.marketplace_config_ids.ref_code', 'product_template_id.marketplace_config_ids.ref_code')
    def _compute_marketplace_product(self):
        for rule in self:
            if rule.product_id:
                product_id = rule.product_id.marketplace_config_ids.filtered(lambda rec: rec.product_id == rule.product_id)
                if len(product_id) > 0:
                    rule.marketplace_product = product_id[0]
                    break
            if rule.product_template_id:
                product_template_id = rule.product_template_id.marketplace_config_ids.filtered(lambda rec: rec.product_id == rule.product_template_id)
                if len(product_template_id) > 0:
                    rule.marketplace_product = product_template_id[0]
                    break
            rule.marketplace_product = False

    def unlink(self):
        for rule in self.exists():
            if rule.ref_code:
                api_provider = rule.config_id.api_provider
                api_provider_obj = self.env['%s' % api_provider]
                api_provider_obj._delete_kogan_listing_rule(rule)
        return super(KoganListingRule, self).unlink()







# The Market >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
class TheMarketColorMapping(models.Model):
    _name='themarket.color.mapping'
    _description = 'Color Mapping for The Market'

    name = fields.Char("Color Name", required=True)
    child_colors = fields.Text("Child Colors", help = "Enter Child color comma separated. Child of Red color ie.: Carmine,Crimson,Salmon")
    themarket_ref = fields.Integer("The Market Color ID", required=True)
    themarket_color_code = fields.Char("Color Code", required=True)
    
    
class TheMarketListingRule(models.Model):
    _name = 'themarket.listing.rule'
    _description = 'TheMarket Linsting Rule'
   
    name = fields.Char(required=True, index=True, default='Rule_MM')
    config_id = fields.Many2one('marketplace.config.details', string='Marketplace Application', domain=[('api_provider', '=', 'themarket')], required=True, ondelete='cascade')
    ref_code = fields.Char("TheMarket Style Id", copy=False)
    product_template_id = fields.Many2one('product.template', ondelete='cascade')
    marketplace_product = fields.Many2one('marketplace.product.template', compute='_compute_marketplace_product', domain=[('config_id.api_provider', '=', 'themarket')], readonly=True, store=True)
    is_active = fields.Boolean(string='Is Active',default=True)
    max_buy_qty = fields.Float(string='Maximum Buy Quantity', related='product_template_id.virtual_available', readonly=False)
    listing_price = fields.Float('Price', related='product_template_id.list_price', readonly=False)
    category_number = fields.Many2one('marketplace.product.category', related='product_template_id.themarket_category_id', string='Category', required=True)
    brand = fields.Many2one('marketplace.product.brand', string='Marketplace Brand', related='product_template_id.themarket_brand_id', domain=[('config_id.api_provider', '=', 'themarket')], readonly=False)
    is_product_new = fields.Boolean(string='Brand New', default=True,
        help="Uncheck this box if this product is Used/Refurbished condition.")