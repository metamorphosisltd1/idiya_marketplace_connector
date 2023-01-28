# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from copy import copy
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.base.models.res_partner import _tz_get

_logger = logging.getLogger(__name__)

API_PROVIDER_END_POINT_URL = {
    'tradevine' : 'https://api.tradevine.com',
    'themarket' : 'https://portal.themarket.com'
}


class MarketPlaceConfigDetails(models.Model):
    _name = 'marketplace.config.details'
    _description = 'MarketPlace configuration details'


    def _get_api_provider(self):
        return [
            ('tradevine', 'Tradevine'),
            ('themarket', 'TheMarket')
            ]

    name = fields.Char(string='Application Name', required=True, copy=False)
    #Tradevine
    consumer_key = fields.Char(required_if_api_provider='tradevine', copy=False)
    consumer_secret = fields.Char(required_if_api_provider='tradevine', copy=False)
    access_token_key = fields.Char(required_if_api_provider='tradevine', copy=False)
    access_token_secret = fields.Char(required_if_api_provider='tradevine', copy=False)
    external_trade_me_organisation_name = fields.Char(required_if_api_provider='tradevine', help='Organization name of the marketplace account')
    # TheMarket
    themarket_username = fields.Char(string="Username",required_if_api_provider='themarket', copy=False)
    themarket_password = fields.Char(string="Password",required_if_api_provider='themarket', copy=False)
    themarket_merchantid = fields.Integer("Merchant Id", store =True,copy=False)
    themarket_userkey = fields.Char("User Key", store =True,copy=False)
    themarket_token = fields.Char("Bearer Token", store =True,copy=False)

    # for generate access token(check if it is needed)
    oauth_token = fields.Char(copy=False)
    oauth_token_secret = fields.Char(copy=False)
    # API Base URL
    api_provider = fields.Selection(selection=_get_api_provider, required=True, copy=False)
    api_url = fields.Char(compute="_compute_api_provider_end_point_url", string='API URL')
    active = fields.Boolean(default=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    product_template_ids = fields.One2many('marketplace.product.template', 'config_id', string="Products")
    sale_order_ids = fields.One2many('marketplace.order', 'config_id', string="Sale Order")
    label = fields.Char(compute="_compute_label_for_sync_data")
    tz = fields.Selection(_tz_get, string='Timezone', readonly=False, default=lambda config: config.env.user.tz)  
    location_ids = fields.Many2many('stock.location', string="Inventory Location", copy=False, help='Please select all the inventory locations that you want to sell products on this Marketplace only')


    # for sync details of cron
    created_from = fields.Date()
    created_to = fields.Date()

    # for tradevine fields
    # tradevine_product_count = fields.Char(copy=False)
    # tradevine_last_product_page_number = fields.Integer(copy=False)

    _sql_constraints = [
        ('name', 'unique (name)', 'Marketplace application name must be unique !')
    ]

    @api.depends('api_provider')
    def _compute_api_provider_end_point_url(self):
        for config in self:
            if config.api_provider and API_PROVIDER_END_POINT_URL.get(config.api_provider):
                config.api_url = API_PROVIDER_END_POINT_URL[config.api_provider]
            else:
                config.api_url = ''

    def _compute_label_for_sync_data(self):
        for config in self:
            config.label = 'Import Data from %s' % config.api_provider

    @api.model_create_multi
    def create(self, vals_list):
        records = super(MarketPlaceConfigDetails, self).create(vals_list)
        for record in records:
            api_provider_obj = self.env['{}'.format(record.api_provider)]
            for config in records:
                if config.api_provider == "tradevine":
                    api_provider_obj._load_tradevine_category_for_odoo(config)
                elif config.api_provider == "themarket":
                    api_provider_obj._load_themarket_category_for_odoo(config)
                    api_provider_obj._load_themarket_brands_for_odoo(config)
                    api_provider_obj._load_themarket_colors_for_odoo(config)
        return records

    def action_test_connection(self):
        api_provider_obj = self.env['%s' % self.api_provider]
        if hasattr(api_provider_obj, '_get_%s_product' % self.api_provider):
            # this call for only check test connection
            response = getattr(api_provider_obj, '_get_%s_product' % self.api_provider)(self)
            msg = _('Test call succeeded!')
            if isinstance(response, dict) and not response.get('error_message'):
                if self.api_provider == 'tradevine':
                    msg = _('Test call succeeded: You have %s products in your %s account!' % (response.get('TotalCount'), self.api_provider))
                elif self.api_provider == 'themarket':
                    # api_provider_obj._load_themarket_category_for_odoo(self)
                    api_provider_obj._load_themarket_brands_for_odoo(self)
                    # api_provider_obj._load_themarket_colors_for_odoo(self)
                    msg = _('Test call succeeded: You have %s products in your %s account!' % (response.get('HitsTotal'), self.api_provider))
                raise UserError(msg)
                
            raise UserError(response.get('error_message'))

    def action_get_product(self):
        api_provider_obj = self.env['%s' % self.api_provider]
        if hasattr(api_provider_obj, '_load_%s_product_for_odoo' % self.api_provider):
            response = getattr(api_provider_obj, '_load_%s_product_for_odoo' % self.api_provider)(self)
            msg = response.get('error_message')
            if isinstance(response, dict) and not response.get('error_message'):
                if self.api_provider == 'tradevine':
                    msg = _('Successfully Imported %s products from your %s account!' % (response.get('TotalCount'), self.api_provider))
                if self.api_provider == 'themarket':
                    msg = _('Successfully Imported %s products from your %s account!' % (response.get('HitsTotal'), self.api_provider))
                _logger.info('{}'.format(msg))
            else:
                _logger.error('{}'.format(msg))

    def action_get_order(self):
        api_provider_obj = self.env['%s' % self.api_provider]
        if hasattr(api_provider_obj, '_load_%s_order_for_odoo' % self.api_provider):
            response = getattr(api_provider_obj, '_load_%s_order_for_odoo' % self.api_provider)(self)
            msg = response.get('error_message')
            if isinstance(response, dict) and not response.get('error_message'):
                if self.api_provider == 'tradevine':
                    msg = _('Successfully Imported %s sale order from your %s account!' % (response.get('TotalCount'), self.api_provider))
                elif self.api_provider == 'themarket':
                    msg = _('Successfully Imported %s sale order from your %s account!' % (response.get('HitsTotal'), self.api_provider))
                _logger.info('{}'.format(msg))
            else:
                _logger.error('{}'.format(msg))

    def cron_fetch_online_sale_order_from_marketplace(self):
        for config in self.search([]):
            api_provider_obj = self.env['%s' % config.api_provider]
            if hasattr(api_provider_obj, 'cron_fetch_online_sale_order_%s' % config.api_provider):
                response = getattr(api_provider_obj, 'cron_fetch_online_sale_order_%s' % config.api_provider)(config) 
                if isinstance(response, dict) and not response.get('error_message'):
                    msg = _('Successfully Imported sale order from your %s account!' % (config.api_provider))
                    _logger.info('{}'.format(msg))
                else:
                    msg = response.get('error_message')
                    _logger.error('{}'.format(msg))
