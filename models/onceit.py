import logging
import json
import time
import requests
import dateutil.parser
import pytz
from datetime import datetime, timedelta
from werkzeug.urls import url_quote
from odoo.exceptions import UserError
from odoo import fields, models, _
from odoo.osv import expression

_logger = logging.getLogger(__name__)

class Onceit(models.AbstractModel):
    _name = 'onceit'
    _description = 'Onceit API'
    
    
    
    
 ###  Onceit Oauth >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_onceit_oauth_header(self, api_provider_config):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': api_provider_config.shop_key
        }
        return headers    
    
    
    
    
# Category for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>        
    def _import_category_from_onceit(self, config, datas):
        categories = [{
            'name': data['label'],
            'parent_id': False,
            'parent_number': data['parent_code'],
            'marketplace_catg_ref_number': data['code'],
            'marketplace_config_id': config.id
        } for data in datas]
        records = self.env['marketplace.product.category']

        for categ in categories: 
            parent = records.search([('marketplace_catg_ref_number', '=', categ.get('parent_number'))])
            if parent:
                categ['parent_id'] = parent.id
            categ.pop('parent_number')
            onceit_categ = records.search([['marketplace_catg_ref_number', '=', categ['marketplace_catg_ref_number']]], limit=1)
            if not onceit_categ:
                records |= records.create(categ)
            else:
                onceit_categ.write(categ)
                
            self.env.cr.commit()
     
     
          
               
# Load Onceit Categories for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _load_onceit_category_for_odoo(self, provider_config):
        _logger.info("_load_onceit_category_for_odoo loaded with {}".format(provider_config))
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/hierarchies'
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            hierarchies = resp.get('hierarchies', False)
            if hierarchies:
                self._import_category_from_onceit(provider_config, hierarchies)
            
        return resp
    
    


# Product Data >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_post_data(self, products):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        products_list = []
        for product in products:
            if product.is_published == True:
                products_list.append({
                    'sku': product.default_code if product.default_code else product.product_sku,
                    'product_id': product.name or product.display_name,
                    'product-id-type' : product.website_description,
                    "price":product.list_price,
                    "state" : "new",
                    'quantity' : product.qty_available,
                    'product-tax-code' : ""
                    })
            else:
                raise UserError("%s is not Published." % product.name)
        
        filename = "file.json"
        with open(filename, "w") as outfile:
            json.dump(products_list, outfile)
        raise UserError("{}".format(json.dumps(products_list)))
        return products_list


    
# Post Onceit Product >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _post_onceit_product(self, provider_config, product, config_field):
        ConfigApp = product.mapped('%s' % config_field).filtered(
            lambda config: config.config_id == provider_config)
        data = self._prepare_product_post_data(product)
        
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='api/products/imports',
            data=json.dumps(data)
        )