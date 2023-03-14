import logging
import json
import time
import requests
import dateutil.parser
import base64
import pytz
from datetime import datetime, timedelta
from werkzeug.urls import url_quote
from odoo.exceptions import UserError
from odoo import fields, models, _
from odoo.osv import expression
from ...marketplace_connector.models import kogan_lookup


_logger = logging.getLogger(__name__)


class Kogan(models.AbstractModel):
    _name = 'kogan'
    _description = 'Kogan API'
    
    
 
 ###  Kogan Oauth >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_kogan_oauth_header(self, api_provider_config):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'SellerToken': api_provider_config.seller_token,
            'SellerID': api_provider_config.seller_id,
        }
        return headers
    



# Category for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>        
    def _import_category_from_kogan(self, config, datas):
        # _logger.info("_import_category_from_kogan with {} categories".format(len(datas)))
        categories = [{
            'name': data['title'],
            'parent_id': False,
            'parent_number': data['parent_category'],
            'marketplace_catg_ref_number': data['id'],
            'marketplace_path': data['url'],
            'marketplace_config_id': config.id,
        } for data in datas]
        records = self.env['marketplace.product.category']
        # _logger.info("_import_category_from_kogan with {} categories".format(len(categories)))

        for categ in categories: 
            parent = records.search([('marketplace_catg_ref_number', '=', categ.get(
                'parent_number'))])
            if parent:
                categ['parent_id'] = parent.id
            categ.pop('parent_number')
            kogan_categ = records.search([['marketplace_catg_ref_number', '=', categ['marketplace_catg_ref_number']]], limit=1)
            if not kogan_categ:
                records |= records.create(categ)
                # _logger.info("_import_category_from_kogan records |= records.create(categ) {}".format(records))
            else:
                kogan_categ.write(categ)
                # _logger.info("_import_category_from_kogan kogan_categ.write(categ) {}".format(kogan_categ))
                
            self.env.cr.commit()
          
               
# Load Kogan Categories for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _load_kogan_category_for_odoo(self, provider_config):
        _logger.info("_load_kogan_category_for_odoo loaded with {}".format(provider_config))
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='category',
            params={"display_all":1},
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            body = resp.get('body', False)
            if body:
                self._import_category_from_kogan(provider_config, body["results"])
            
        return resp 


     
     
# Brand for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>        
    def _import_brand_from_kogan(self, config, datas):
        brands = [{
            'name': data['title'],
            'config_id': config.id,
            'description': data['description'],
            'ref_code': data['id']
        } for data in datas]
        records = self.env['marketplace.product.brand']

        for brand in brands: 
            kogan_brand = records.search([['ref_code', '=', brand['ref_code']]], limit=1)
            if not kogan_brand:
                records |= records.create(brand)
            else:
                kogan_brand.write(brand)
             
            self.env.cr.commit()
          


            
# Load Kogan Brands for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _load_kogan_brand_for_odoo(self, provider_config):
        # _logger.info("_load_kogan_brand_for_odoo loaded with {}".format(provider_config))
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='brand',
            params={"display_all":1},
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            body = resp.get('body', False)
            if body:
                self._import_brand_from_kogan(provider_config, body["results"])
            
        return resp 

     
     
     
    
#GET PRODUCT >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_kogan_product_by_id(self, provider_config, product_id, **kwargs):
        '''This method gets an individual product specified by the supplied ID - 
            the output consists of top level product information, including summary inventory quantities
        '''
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='products/%s' % product_id,
            params={"enabled":1}
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            body = resp.get('body', False)
            if body:
                return body['results']

    def _get_kogan_product_by_paged_list(self, provider_config, **kwargs):
        ''' This method gets a paged list of top level product information, including summary inventory quantities. '''

        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='products',
            params = {"enabled":1}
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            body = resp.get('body', False)
            if body:
                return body['results']

    def _get_kogan_product(self, provider_config, product_id=None, **kwargs):
        if product_id:
            return self._get_kogan_product_by_id(provider_config, product_id, **kwargs)
        if not product_id:
            return self._get_kogan_product_by_paged_list(provider_config, **kwargs)


    













                           ########### PUSH PRODUCT ############

# Update product Stock >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _update_kogan_product_stock(self, ConfigApp, config, product, location_ids=False, sale_order=False):
        ConfigApp = product.mapped('marketplace_config_ids').filtered(
            lambda m_config: m_config.config_id == config and m_config.ref_code)
        ProductID = ConfigApp.mapped("ref_code")[-1] if ConfigApp else False
        _logger.warning("Updating stock of {} : {} ref {}".format(product.name, product.id, ProductID))
        if ProductID:
            data = self._prepare_product_post_stock_data(product)
            data.update({'ProductID': ProductID})

            _logger.warning("kogan ProductInventory MakeAdjustment body {}".format(json.dumps(data)))
            resp = self.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=config,
                http_method='POST',
                service_endpoint='products/stockprice',
                data=json.dumps(data),
            )
            if isinstance(resp, dict) and not resp.get('error_message'):
                self._prepare_product_update_vals(config, product, resp)
            return resp
        return {'error_message': _('Product ID is missing for kogan stock adjustment')}
    

    
    
    def _prepare_product_post_stock_data(self, product, location_ids=False, sale_order=False, default_type=None):
        values = {
            'product_sku': product.default_code if product.default_code else product.product_sku,
            "offer_data" : {
                            "NZD": {"price":product.list_price,
                                    "handling_days": 0}},
            'stock' : product.qty_available,
            'enabled': product.is_published
        }
        return values







# Product Async Task >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_product_async_task(self, ConfigApp, provider_config, product, resp, data):
        if resp.get('pending_url'):
            task_url = resp.get('pending_url')
            task_id = task_url.split("/")[-2]
            asnc_task = self.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=provider_config,
                http_method='GET',
                service_endpoint='task/%s' %task_id,
                params= {"task_id": task_id}
            )

            if isinstance(asnc_task, dict) and (asnc_task.get('status') == "CompleteWithErrors"):
                raise UserError("{}".format(json.dumps(asnc_task.get("body").get("errors"))))
            
            else:
                self._prepare_product_update_vals(provider_config, product, data)
                raise UserError("Product pushed to Kogan Successfully ...")
            
    
# Product Update Value to Marketplace Product Template >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_update_vals(self, provider_config, products, data):
        # for product in products:
        for datam in data:
            product_variant = self.env['product.product'].search([('default_code', '=', datam['product_sku'])], limit=1)
            if product_variant:
                product_template_id = product_variant.product_tmpl_id.id
                product_template = self.env['marketplace.product.template'].create({
                    'name': provider_config.api_provider,
                    'ref_code': datam['product_sku'],
                    'config_id': provider_config.id,
                    # 'product_template_id': products.id if products._name == 'product.template' else False,
                    'product_template_id': product_template_id,
                    # 'product_id': products.id if products._name == 'product.product' else products.product_variant_id.id,
                    'product_id': product_variant.id,
                    'category_ref_id': product_variant.kogan_category_id.marketplace_catg_ref_number,
                    'product_qty' : datam['stock']
                })
                self.env.cr.commit()
            
# Prepare product details during creation in KOGAN >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_create_details(self, provider_config, resp, data):
        product_detail = self.env['product.create.detail'].create({
            'name': provider_config.api_provider,
            'config_id': provider_config.id,
            'kogan_async_link': resp.get("pending_url"),
            'request_data': json.dumps(data)
        })
        self.env.cr.commit()



# Product Data >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_post_data(self, products):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        products_list = []
        for product in products:
            if product.is_published == True:
                taxes_id = product.taxes_id
                if not taxes_id:
                    taxes_id = self.env['account.tax'].sudo().search([['id','=',2]])
                    product.taxes_id = [(4,taxes_id.id)]
                
                images = []
                if product._get_images():
                    for image in product._get_images():
                        image_url = "{}/web/image?model={}&field=image_1920&id={}".format(base_url,image._name,image.id)
                        images.append(image_url)
            
                variant_data = {"group_title": "{}_{}".format(product.name,product.kogan_facet_group),
                                "group_id": "{}_{}_id".format(product.name,product.kogan_facet_group),}
                
                # attributes= product.product_variant_ids.mapped('product_template_attribute_value_ids').mapped('attribute_id')
                # v_count=0
                # for att in attributes:
                #     length= "_{}".format(v_count+1) if v_count > 0 else ''
                #     variant_data.update({
                #                     "vary_on{}".format(length):{
                #                                             "group" : product.kogan_facet_group,
                #                                             "type" : att.name
                #                                         }
                #                 })
                #     v_count+=1
                
                
                # if product.product_variant_ids:
                if product.product_variant_count > 1 :
                    for variant in product.product_variant_ids:
                        prod_sku = variant.default_code
                        
                        facet = [{
                                    "group": product.kogan_facet_group,
                                    "items": [
                                        {
                                            "type": att_val.attribute_id.name,
                                            "value": att_val.name
                                        }for att_val in variant.product_template_attribute_value_ids]
                                    }]
                        
                        # variant_image = variant.product_variant_image_ids
                        # if variant_image :
                        #     for images in variant_image:
                        #         image_new = base64.b64encode(images).decode('utf-8')
                        image_new = variant.product_variant_image_ids.name
                        
                        v_count=0
                        for item in facet[0]["items"]:
                            length= "_{}".format(v_count+1) if v_count > 0 else ''
                            variant_data.update({
                                            "vary_on{}".format(length):{
                                                        "group" : facet[0]["group"],
                                                        "type" : item["type"]
                                                                    }
                                            })
                            v_count+=1
                            
                        products_list.append({
                            'product_sku': prod_sku,
                            'product_title' : variant.name,
                            # 'product_description' : product.website_description,
                            'category' : "kogan:{}".format(product.kogan_category_id.marketplace_catg_ref_number),
                            'images' : image_new,
                            # 'stock' : product.avail_instock_qty,
                            "offer_data" : {
                                            "NZD": {"price":product.list_price,
                                                    "handling_days": 0}},
                            # "product_dimensions" : {
                            #                     "length": product.length if product.length else "",
                            #                     "width" : product.width if product.width else "",
                            #                     "height" : product.height if product.height else "",
                            #                     "weight" : product.weight if product.weight else ""
                            #                     },
                            "product_gtin" : product.barcode if product.barcode else "",
                            'enabled': product.is_published,
                            'brand': product.kogan_brand_id.name,
                            "facets" : facet,
                            "variant": variant_data
                        })
                else :
                    products_list.append({
                        'product_sku': product.default_code if product.default_code else product.product_sku,
                        'product_title': product.name or product.display_name,
                        'product_description' : product.website_description,
                        'category' : "kogan:{}".format(product.kogan_category_id.marketplace_catg_ref_number),
                        'images' : images,
                        'stock' : product.avail_instock_qty,
                        "offer_data" : {
                                        "NZD": {"price":product.list_price,
                                                "handling_days": 0}},
                        "product_dimensions" : {
                                                "length": product.length if product.length else "",
                                                "width" : product.width if product.width else "",
                                                "height" : product.height if product.height else "",
                                                "weight" : product.weight if product.weight else ""
                                                },
                        "product_gtin" : product.barcode if product.barcode else "",
                        'enabled': product.is_published,
                        'brand': product.kogan_brand_id.name  
                        })
            else:
                raise UserError("%s is not Published." % product.name)
        
        raise UserError("{}".format(json.dumps(products_list)))
        return products_list
    
        
                
# Post Kogan Product >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _post_kogan_product(self, provider_config, product, config_field):
        ConfigApp = product.mapped('%s' % config_field).filtered(
            lambda config: config.config_id == provider_config)
        data = self._prepare_product_post_data(product)
        
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='products/',
            data=json.dumps(data)
        )
        self._prepare_product_create_details(provider_config, resp, data)
        if isinstance(resp, dict) and (resp.get('status') != "Failed"):
            self._get_product_async_task(ConfigApp, provider_config, product, resp, data)
        else:
            raise UserError("{}".format(json.dumps(resp.get("error"))))
        return resp

















































                            ############# KOGAN ORDER ##################


# Get All Open Order >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_status_for_order(self):
        statuses = ["ReleasedForShipment", "Pending", "AcknowledgedBySeller", "PartiallyShipped", "Shipped", "Canceled"]
        
    def _get_all_open_order(self, provider_config, params):
        params = {
            'status': self._get_status_for_order(),
        }
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='orders/?status=%s' % params.get("status"),
            params=params,
        )
        if isinstance(resp, dict) and (resp.get('status') != "Failed"):
            pass
        
        
        
        
        
        
# Get Order By ID >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_kogan_order_ref(self):
        pass
        # try:
        #     raise UserError("Please enter a value for 'input':")
        # except UserError as e:
        #     input_value = input(str(e.args[0]) + "\n")
    
    
    def _get_order_by_id(self, provider_config, params):
        params = {
            "kogan_order_ref" : self._get_kogan_order_ref()
        }
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='orders/:%s' % params.get("kogan_order_ref"),
            params=params,
            data={},
        )
        if isinstance(resp, dict) and (resp.get('status') != "Failed"):
            pass




# Prepare Product Dispatch Order >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_dispatch_data(self):
        data = [{
                "ID": "proident eu adipisicing laboris",
                "Items": [
                    {
                    "OrderItemID": "102025",
                    "SellerSku": "Excepteur et",
                    "Quantity": 5,
                    "ShippedDateUtc": "2010-06-29T12:21:28.422Z",
                    "TrackingNumber": "ad",
                    "ShippingCarrier": "sint consectetur proident cillum"
                    }
                ]
                }
                ]
        return data
    
    
    def _post_order_dispatch_information(self, provider_config):
        
        data = self._prepare_product_dispatch_data()
        
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='orders/fulfill',
            data=json.dumps(data),
        )
        
        if isinstance(resp, dict) and (resp.get('status') != "Failed"):
            pass
        
        
        
        
# Post Order Cancel Request >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _post_order_cancel_request(self, provider_config, params):
        params = {
            "kogan_order_ref" : self._get_kogan_order_ref()
        }
        data = self._prepare_product_dispatch_data()
        
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='orders/%s/cancel' % params.get("kogan_order_ref"),
            data=json.dumps(data),
        )

        if isinstance(resp, dict) and (resp.get('status') != "Failed"):
            pass




# Post Order Refund Request >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _post_order_refund_request(self, provider_config, params):
        params = {
            "kogan_order_ref" : self._get_kogan_order_ref()
        }
        data = self._prepare_product_dispatch_data()
        
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='orders/%s/refund' % params.get("kogan_order_ref"),
            data=json.dumps(data),
        )

        if isinstance(resp, dict) and (resp.get('status') != "Failed"):
            pass

















#Prepare PRODUCT Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>)))))))) 
    def _prepare_product_values(self, product_values, config):
        currency = self.env['res.currency']
        marketplace_brand = self.env['marketplace.product.brand']

        if product_values.get('brand'):
            marketplace_brand = marketplace_brand.search(
                [('name', '=', product_values['brand'])], limit=1)
            if not marketplace_brand:
                marketplace_brand = marketplace_brand.create(
                    {
                        'name': product_values['brand'],
                        'config_id' : config.id                    
                    })

        return {
            'name': product_values['product_title'],
            'code': product_values['product_sku'],
            'description': product_values.get('product_description'),
            'description_sale': product_values.get('product_inbox'),
            'standard_price': product_values.get('offer_data').get("NZD").get("price"),
            'lst_price': product_values.get('offer_data').get("NZD").get("price"),
            'list_price': product_values.get('offer_data').get("NZD").get("price"),
            'weight': product_values.get('product_dimensions').get("weight"),
            'currency_id': currency.id,
            'marketplace_brand_id': marketplace_brand.id if marketplace_brand else product_values.get('brand'),
            'active': not product_values.get('enabled')
        }
      
    
#GET Customer Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_customer_values(self, customer_values, billing_address, shipping_address):
        marketplace_partner_obj = self.env['marketplace.res.partner']
        config = self.env.context.get('config')
        partner_obj = self.env['res.partner']
        customers = [partner_obj, partner_obj, partner_obj]
        i = 0
        if customer_values.get('CustomerID'):
            marketplace_partner_obj = marketplace_partner_obj.search(
                [('ref_code', '=', customer_values['CustomerID'])], limit=1)
            customer = marketplace_partner_obj.partner_id
            billing_address_id = marketplace_partner_obj.default_billing_address_id
            shipping_address_id = marketplace_partner_obj.default_shipping_address_id
            customers[i] = customer
    
        if not marketplace_partner_obj and customer_values.get('CustomerID'):
            customer_list = []
            billing_address_id, shipping_address_id = False, False
            customer_id = customer_values.get('CustomerID')
            customer_values.update({'need_to_create_address': True})
            if billing_address and billing_address.get('CustomerID') == customer_id:
                billing_address_id = billing_address.get('AddressID')
                if customer_values.get('DefaultBillingAddressID') != billing_address_id:
                    billing_address.update({'need_to_create_address': True})
                    
            if shipping_address and shipping_address.get('CustomerID') == customer_id:
                shipping_address_id = shipping_address.get('AddressID')
                if customer_values.get('DefaultShippingAddressID') != billing_address_id:
                    shipping_address.update({'need_to_create_address': True})
                    
            if (billing_address_id and shipping_address_id) and shipping_address_id == billing_address_id:
                customer_values.update({
                    'AddressLine1': billing_address['AddressLine1'],
                    'AddressLine2': billing_address['AddressLine2'],
                    'AddressLine3': billing_address['AddressLine3'],
                    'TownCity': billing_address['TownCity'],
                    'RegionState': billing_address['RegionState'],
                    'PostalCode': billing_address['PostalCode'],
                    'Country': billing_address['Country'],
                    'CountryCode': billing_address['CountryCode'],
                })
                customer_list.extend([customer_values])
            else:
                if billing_address_id:
                    customer_values.update({
                        'AddressLine1': billing_address['AddressLine1'],
                        'AddressLine2': billing_address['AddressLine2'],
                        'AddressLine3': billing_address['AddressLine3'],
                        'TownCity': billing_address['TownCity'],
                        'RegionState': billing_address['RegionState'],
                        'PostalCode': billing_address['PostalCode'],
                        'Country': billing_address['Country'],
                        'CountryCode': billing_address['CountryCode'],
                    })
                customer_list.extend(
                    [customer_values, billing_address, shipping_address])
                
            parent = False
            for values in customer_list:
                if values:
                    new_customer_values = self.with_context(need_to_create_address=values.get(
                        'need_to_create_address', True))._create_new_kogan_customer_values(values, parent)
                    new_customer = partner_obj
                    if new_customer_values:
                        address_id = new_customer_values.pop('address_id')
                        new_customer = partner_obj.create(new_customer_values)
                        marketplace_partner_obj.create({
                            'name': config.name,
                            'config_id': config.id,
                            'ref_code': customer_values['CustomerID'] if not new_customer_values.get('type') else address_id,
                            'default_billing_address_id': customer_values['DefaultBillingAddressID'] if not new_customer_values.get('type') else False,
                            'default_shipping_address_id': customer_values['DefaultShippingAddressID'] if not new_customer_values.get('type') else False,
                            'partner_id': new_customer.id,
                        })
                        parent = new_customer
                    customers[i] = new_customer
                i += 1
        return tuple(customers)


# New Customer Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>  
    def _create_new_kogan_customer_values(self, values, parent=False):
        if not self.env.context.get('need_to_create_address'):
            return {} 
        customer_value = {}
        state = self.env['res.country.state']
        country = self.env['res.country']
        if values.get('FirstName'):
            name = values['FirstName']
            if name and values.get('LastName'):
                name = name + ' ' + values['LastName']
            customer_value = {
                'name': name,
                'email': values['Email'],
                'mobile': values.get('MobileNumber', 'PhoneNumber'),
                'comment': values.get('Notes'),
                'vat': values.get('TaxNumber'),
                'address_id': False,
            }
        if values.get('Addresss'):
            address = values.get('Addresss')
            if address.get('RegionState'):
                state_name = kogan_lookup.get_regions_and_states(
                    address['RegionState'])
                state = state.search([('name', '=', state_name)], limit=1)
            if address.get('Country'):
                country_name = kogan_lookup.get_country(address['Country'])
                country = country.search(
                    [('name', '=', country_name)], limit=1)

            customer_value.update({
                'street': address['AddressLine1'],
                'street2': address['AddressLine2'] + address.get('AddressLine3', ' '),
                'city': address['TownCity'],
                'state_id': state.id,
                'zip': address['PostalCode'],
                'country_id': country.id,
            })
        else:
            if not parent and values:
                if values.get('RegionState'):
                    state_name = kogan_lookup.get_regions_and_states(
                        values['RegionState'])
                    state = state.search([('name', '=', state_name)], limit=1)
                if values.get('Country'):
                    country_name = kogan_lookup.get_country(
                        values['Country'])
                    country = country.search(
                        [('name', '=', country_name)], limit=1)
                street2 = False
                if values.get('AddressLine2'):
                    street2 = values.get('AddressLine2')
                    if street2 and values.get('AddressLine3'):
                        street2 += values['AddressLine3']
                else:
                    street2 = values.get('AddressLine3')
                customer_value.update({
                    'street': values.get('AddressLine1'),
                    'street2': street2,
                    'city': values.get('TownCity'),
                    'state_id': state.id,
                    'zip': values.get('PostalCode'),
                    'country_id': country.id,
                })
            if parent and values:
                customer_value.update({
                    'parent_id': parent.id,
                    'name': parent.name,
                    'email': parent.email,
                    'mobile': parent.mobile,
                    'comment': parent.comment,
                    'type': values['type'],
                    'address_id': values['AddressID'],
                })
        return customer_value
    
    
    
#Prepare order line >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_order_line_values(self, config, order_line_values):
        product_obj = self.env['product.product']
        marketplace_product_obj = self.env['marketplace.product.template']
        vals = []
        for order_line_value in order_line_values:
            domain = [('marketplace_config_ids.ref_code',
                       '=', order_line_value['ProductID'])]
            if order_line_value.get('Barcode'):
                domain = expression.OR(
                    [domain, [('barcode', '=', order_line_value.get('Barcode'))]])
            product_id = product_obj.search(domain, limit=1)
            if not product_id:
                product_id = product_obj.create(
                    self._prepare_product_values(order_line_value, config))
                marketplace_order = marketplace_product_obj.search(
                    [('ref_code', '=', order_line_value['ProductID'])], limit=1)
                if not marketplace_order:
                    product_id.marketplace_config_ids = [(0, 0, {
                        'name': config.name,
                        'config_id': config.id,
                        'product_template_id': product_id.product_tmpl_id.id,
                        'product_id': product_id.id,
                        'ref_code': order_line_value['ProductID'],
                    })]
                else:
                    product_id.marketplace_config_ids = [
                        (4, marketplace_order.id)]

            vals.append((0, 0, {
                'product_id': product_id.id,
                'product_uom_qty': order_line_value.get('Quantity', 1.0),
                'price_unit': order_line_value.get('SellPrice')
            }))
        return vals
    
    
#Prepare Order Values >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_order_values(self, config, order_values):
        self = self.with_context(config=config)
        BillingAddress = order_values['BillingAddress']
        ShippingAddress = order_values['ShippingAddress']
        if BillingAddress:
            BillingAddress.update({'type': 'invoice'})
        if ShippingAddress:
            ShippingAddress.update({'type': 'delivery'})
            
        cus_mar_ref = order_values.get('CustomerOrderReference') or False


        customer, invoice_address, shipping_address = self._prepare_customer_values(
            order_values['Customer'], BillingAddress, ShippingAddress)
        currency = self.env['res.currency']
        if order_values['Currency']:
            currency_name = kogan_lookup.get_currency(
                order_values['Currency'])
            currency = currency.search([('name', '=', currency_name)], limit=1)
        warehouse = self.env['stock.warehouse']
        if order_values.get('WarehouseCode'):
            warehouse = warehouse.search(
                [('code', '=', order_values['WarehouseCode'])], limit=1)
            if not warehouse:
                warehouse = warehouse.search([], limit=1)
                
        return {
            'name': order_values['OrderNumber'],
            'date_order': dateutil.parser.parse(order_values['CompletedDate']).strftime("%Y-%m-%d %H:%M:%S") if order_values.get('CompletedDate') else fields.Datetime.now(),
            'partner_id': customer.id,
            'order_line': self._prepare_order_line_values(config, order_values.get('SalesOrderLines', [])),
            'company_id': self.env.company.id,
            'origin': kogan_lookup.get_order_origin(order_values['OrderOrigin']),
            'team_id': config.team_id.id,
            'commitment_date': dateutil.parser.parse(order_values['RequestedShippingDate']).strftime("%Y-%m-%d") if order_values.get('RequestedShippingDate') else False,
            'currency_id': currency.id if currency else self.env.company.currency_id.id,
            'warehouse_id': warehouse.id,
            'partner_invoice_id': invoice_address.id or customer.id,
            'partner_shipping_id': shipping_address.id or customer.id,
        }
        
    
#Order for odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_kogan_order_by_paged_list(self, provider_config, pageNumber=1, pageSize=499, **kwargs):
        ''' This method gets a paged list of top level product information, including summary inventory quantities. '''
        params = {
            'pageNumber': pageNumber,
            'pageSize': pageSize,
            **kwargs
        }
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='orders',
            params=params,
            data={},
        )
        
    def _load_kogan_order_for_odoo(self, provider_config, pageNumber=1, pageSize=499, createdFrom=None, createdTo=None):
        response = self._get_kogan_order_by_paged_list(
            provider_config, pageNumber, pageSize, createdFrom=createdFrom, createdTo=createdTo) or {}
        total_order = response.get('CountTotal')
        load_order = 0
        sale_order_obj = self.env['sale.order']
        marketplace_order_obj = self.env['marketplace.order']
        while True:
            order_values = []
            if response.get('List') and (total_order - load_order) > 0:
                for order in response['List']:
                    SalesOrderID = order.get('SalesOrderID')
                    CustomerOrderReference = order.get('CustomerOrderReference')
                    domain = ['|',
                        ('marketplace_config_id.ref_code', '=', SalesOrderID), ('reference', '=', CustomerOrderReference)]
                    if not sale_order_obj.search(domain, limit=1):
                        vals = self._prepare_order_values(
                            provider_config, order)
                        marketplace_order = marketplace_order_obj.search(
                            [('ref_code', '=', SalesOrderID)], limit=1)
                        if vals:
                            vals.update({
                                'marketplace_config_id': marketplace_order_obj.create({
                                    'name': provider_config.name,
                                    'config_id': provider_config.id,
                                    'ref_code': SalesOrderID,
                                }).id if not marketplace_order else marketplace_order.id
                            })
                            
                            order_values.append(vals)
                _logger.warning('kogan Order values {}'.format(order_values))
                if order_values:
                    saleOrders = sale_order_obj.create(order_values)
                    for saleOrder in saleOrders:
                        saleOrder.marketplace_config_id.sale_order_ref = saleOrder.name
                        if saleOrder.payment_status == 'complete':
                            saleOrder.action_confirm()

                    sale_order_obj.env.cr.commit()

                load_order += len(response['List'])
                if load_order != total_order:
                    pageNumber += 1
                    response = self._get_kogan_order_by_paged_list(
                        provider_config, pageNumber, pageSize, createdFrom=createdFrom, createdTo=createdTo) or {}
            else:
                break
        return response
    


# Prepare order update values >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_order_update_vals(self, provider_config, config_app, order, resp):
        if config_app:
            return config_app.write({
                'ref_code': resp.get('SalesOrderID'),
            })
        else:
            order.marketplace_config_id = self.env['marketplace.order'].create({
                'name': provider_config.api_provider,
                'config_id': provider_config.id,
                'ref_code': resp.get('SalesOrderID'),
            })
            return order.marketplace_config_id



# Prepare order Line update values >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_order_line_update_vals(self, provider_config, config_app, order_line, resp):
        if config_app:
            return config_app.write({
                'ref_code': resp.get('SalesOrderID'),
            })
        else:
            order_line.marketplace_config_id = self.env['marketplace.order.line'].create({
                'name': provider_config.api_provider,
                'config_id': provider_config.id,
                'ref_code': resp.get('SalesOrderLineID'),
            })
            return order_line.marketplace_config_id



# Prepare Sale order Line post data >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_sale_order_line_post_data(self, provider_config, order_line):
        order_line = []
        for line in order_line:
            order_line.append({
                'SalesOrderLineID': line.marketplace_config_id.ref_code or False,
                'LineNumber': order_line.id,
                'ProductID': line.marketplace_config_ids.filtered(lambda config: config.config_id == provider_config).ref_code or False,
                'Code': line.product_id.default_code,
                'Name': line.product_id.name,
                'Barcode': line.product_id.barcode,
                'Quantity': line.product_uom_qty,
                'CostPrice': line.product_id.standard_price,
                'SellPrice': line.price_unit,
                'LineNotes': line.name,
                'LineTotal': line.price_subtotal,
            })
        return order_line




# Prepare Sale order post data >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_sale_order_post_data(self, provider_config, order):
        partner = order.partner_id
        customer_name = partner.name.split(' ')
        FirstName = customer_name[0]
        LastName = customer_name[1] if len(customer_name) > 1 else ''
        if self.user_has_groups('sale.group_sale_delivery_address'):
            BillingAddress = order.partner_invoice_id
            ShippingAddress = order.partner_shipping_id
        else:
            BillingAddress = partner
            ShippingAddress = partner
        return {
            'OrderNumber': order.name,
            'OrderOrigin': order.origin,
            'Status': 12001,
            'Currency': 10150,  # lookup value
            # 'WarehouseID': ,
            # 'WarehouseCode':,
            'CompletedDate': order.date_order,
            'RecipientName': partner.name,
            'PaymentType': 26001,
            'ShipmentType': 25004,  # lookup value
            'RequestedShippingDate': order.commitment_date or False,
            'Customer': {
                'CustomerID': partner.marketplace_config_ids.filtered(lambda config: config.config_id == provider_config).ref_code or False,
                'FirstName': FirstName,
                'LastName': LastName,
                'Email': partner.email,
                'MobileNumber': partner.mobile,
                'PhoneNumber': partner.phone,
                'CustomerCode': partner.title,
                'Notes': partner.comment,
                'TaxNumber': partner.vat,
                'Addresss': [],
            },
            'BillingAddress': {
                'AddressID': BillingAddress.marketplace_config_ids.filtered(lambda config: config.config_id == provider_config).ref_code or False,
                'CustomerID': partner.marketplace_config_ids.filtered(lambda config: config.config_id == provider_config).ref_code or False,
                'AddressLine1': BillingAddress.street,
                'AddressLine2': BillingAddress.street2,
                'TownCity': BillingAddress.city,
                'RegionState': 60162,  # look up value
                'PostalCode': 8054,  # look up value
                'Country': 8157,  # look up value
                # 'DeliveryNotes': BillingAddress,
            },
            'ShippingAddress': {
                'AddressID': BillingAddress.marketplace_config_ids.filtered(lambda config: config.config_id == provider_config).ref_code or False,
                'CustomerID': partner.marketplace_config_ids.filtered(lambda config: config.config_id == provider_config).ref_code or False,
                'AddressLine1': ShippingAddress.street,
                'AddressLine2': ShippingAddress.street2,
                'TownCity': ShippingAddress.city,
                'RegionState': 60162,  # look up value
                'PostalCode': 8054,  # look up value
                'Country': 8157,  # look up value
                # 'DeliveryNotes': ShippingAddress,
            },
            'SalesOrderLines': self._prepare_sale_order_line_post_data(provider_config, order.order_line)
        }




# Post Kogan Sale Order >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _post_kogan_sale_order(self, provider_config, order, config_field, params=None):
        ConfigApp = order.mapped('%s' % config_field)
        SaleOrderID = ConfigApp.ref_code
        data = self._prepare_sale_order_post_data(provider_config, order)
        if SaleOrderID:
            data.update({'SalesOrderID': SaleOrderID})
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='SalesOrder/%s' % SaleOrderID if SaleOrderID else 'SalesOrder',
            params=params or {},
            data=json.dumps(data),
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            self._prepare_order_update_vals(
                provider_config, ConfigApp, order, resp)
            for line in order.order_line:
                sale_line = {}
                for o_line in resp.get('SalesOrderLines'):
                    if o_line.get('LineNumber') == line.id:
                        sale_line = o_line
                        break
                self._prepare_order_line_update_vals(
                    provider_config, ConfigApp, line, sale_line)
                self._prepare_product_update_vals(
                    provider_config, ConfigApp, line.product_id, sale_line)
        return resp




# Delete Kogan Listing Rule >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _delete_kogan_listing_rule(self, rule):
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=rule.config_id,
            http_method='POST',
            service_endpoint='KoganListingRule/DeleteRule/%s' % rule.ref_code,
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            return True
        if isinstance(resp, dict) and resp.get('error_message'):
            raise UserError(_("Error! %s" % resp.get('error_message')))
        rule.ref_code = False
        return True



# Fetch online Sale Order >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def cron_fetch_online_sale_order_kogan(self, config_app):
        current_date = fields.Datetime.from_string(
            fields.Date.context_today(self))
        kogan_tz = pytz.timezone(config_app.tz or 'UTC')
        
        start_with_zero_hours = current_date.astimezone(
            kogan_tz).replace(tzinfo=None)
        
        createdFrom = current_date.replace(
            hour=0, minute=0, second=0, microsecond=0)- timedelta(days=7)

        createdTo = current_date.astimezone(
            kogan_tz).replace(tzinfo=None)
        
        createdFrom = '{:%Y-%m-%dT%H:%M:%S.%fz}'.format(createdFrom)
        createdTo = '{:%Y-%m-%dT%H:%M:%S.%fz}'.format(createdTo)
        
        return self._load_kogan_order_for_odoo(
            config_app, pageNumber=1, pageSize=499, createdFrom=createdFrom, createdTo=createdTo)
