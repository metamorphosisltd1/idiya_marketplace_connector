# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint
import random
import re
import pytz
import json
import logging
import requests
import time
import uuid
import urllib.parse
import dateutil.parser
from datetime import datetime, timedelta
import html2text

from werkzeug.urls import url_quote
from lxml import html

from odoo import fields, models, _
from odoo.osv import expression

from odoo.exceptions import UserError

from ...marketplace_connector.models import tradevine_lookup

_logger = logging.getLogger(__name__)


class Tradevine(models.AbstractModel):
    _name = 'tradevine'
    _description = 'Tradevine API'





    def _get_tradevine_oauth_signature(self, consumer_secret, token_secret):
        token_secret = '%26' + token_secret
        return consumer_secret + token_secret

    def _get_tradevine_oauth_header(self, api_provider_config):
        header_params = {
            'oauth_consumer_key': api_provider_config.consumer_key,
            'oauth_token': api_provider_config.access_token_key,
            'oauth_nonce': uuid.uuid4(),
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': 1.0,
        }

        header_params['oauth_signature'] = self._get_tradevine_oauth_signature(
            api_provider_config.consumer_secret, api_provider_config.access_token_secret)
        header_oauth = 'OAuth ' + ', '.join([('%s="%s"' % (key, url_quote(
            header_params[key], unsafe='+:/'))) for key in sorted(header_params.keys())])
        headers = {
            'Authorization': header_oauth,
            'Content-Type': 'application/json',
        }
        return headers





# Get Product >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_tradevine_product_by_id(self, provider_config, product_id, **kwargs):
        '''This method gets an individual product specified by the supplied ID - 
            the output consists of top level product information, including summary inventory quantities
        '''
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='v1/Product/%s' % product_id,
            params={},
            data={},
        )

    def _get_tradevine_product_by_paged_list(self, provider_config, pageNumber=1, pageSize=499, **kwargs):
        ''' This method gets a paged list of top level product information, including summary inventory quantities. '''
        params = {
            'pageNumber': pageNumber,
            'pageSize': pageSize,
            **kwargs
        }
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='v1/Product',
            params=params,
            data={},
        )

    def _get_tradevine_order_by_paged_list(self, provider_config, pageNumber=1, pageSize=499, **kwargs):
        ''' This method gets a paged list of top level product information, including summary inventory quantities. '''
        params = {
            'pageNumber': pageNumber,
            'pageSize': pageSize,
            **kwargs
        }
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='v1/SalesOrder',
            params=params,
            data={},
        )

    def _get_tradevine_product(self, provider_config, product_id=None, **kwargs):
        if product_id:
            return self._get_tradevine_product_by_id(provider_config, product_id, **kwargs)
        if not product_id:
            return self._get_tradevine_product_by_paged_list(provider_config, **kwargs)




#Product Value>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_values(self, product_values, config):
        currency = self.env['res.currency']
        marketplace_brand = self.env['marketplace.product.brand']
        if product_values.get('Currency'):
            currency_name = tradevine_lookup.get_currency(
                product_values['Currency'])
            currency = currency.search([('name', '=', currency_name)], limit=1)
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
            'name': product_values['Name'],
            'code': product_values['Code'],
            'barcode': product_values['Barcode'],
            'description': product_values.get('Description'),
            'description_sale': product_values.get('ExternalNotes'),
            'default_code': product_values.get('AlternateCode'),
            'standard_price': product_values.get('CostPrice'),
            'lst_price': product_values.get('SellPrice'),
            'list_price': product_values.get('SellPrice'),
            'weight': product_values.get('Weight'),
            'currency_id': currency.id,
            'marketplace_brand_id': marketplace_brand.id if marketplace_brand else product_values.get('brand'),
            'is_manual_order_approval_needed': product_values.get('IsManualOrderApprovalNeeded'),
            'active': not product_values.get('IsArchived'),
            'marketplace_enable_inventory': product_values.get('EnableInventory'),
        }





# Get Customer Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
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
                        'need_to_create_address', True))._create_new_tradevine_customer_values(values, parent)
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



# New Customer Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _create_new_tradevine_customer_values(self, values, parent=False):
        if not self.env.context.get('need_to_create_address'):
            return {}
        woo_backend = self.env['wordpress.configure'].sudo().search([],limit=1)
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
                'phone': values.get('PhoneNumber') or False,
                'mobile': values.get('MobileNumber') or False,
                'comment': values.get('Notes'),
                'vat': values.get('TaxNumber'),
                'address_id': False,
                'backend_id': False,
            }
            if woo_backend:
                customer_value.update({
                    'backend_id' : woo_backend.id
                })

        if values.get('Addresss'):
            address = values.get('Addresss')
            if address.get('RegionState'):
                state_name = tradevine_lookup.get_regions_and_states(
                    address['RegionState'])
                state = state.search([('name', '=', state_name)], limit=1)
            if address.get('Country'):
                country_name = tradevine_lookup.get_country(address['Country'])
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
                    state_name = tradevine_lookup.get_regions_and_states(
                        values['RegionState'])
                    state = state.search([('name', '=', state_name)], limit=1)
                if values.get('Country'):
                    country_name = tradevine_lookup.get_country(
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



# Prepare Order Line >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
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


# Prepare Order Values >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
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
            currency_name = tradevine_lookup.get_currency(
                order_values['Currency'])
            currency = currency.search([('name', '=', currency_name)], limit=1)
        warehouse = self.env['stock.warehouse']
        if order_values.get('WarehouseCode'):
            warehouse = warehouse.search(
                [('code', '=', order_values['WarehouseCode'])], limit=1)
            if not warehouse:
                warehouse = warehouse.search([], limit=1)
                
                
        marketplace_list_id = self.env['marketplace.list'].search([('marketplace_id', '=', config.id)], limit=1)
        woo_backend = self.env['wordpress.configure'].sudo().search([],limit=1)
        payment_status = 'pending'
        acqurer_name = False 
        if 'IsPaymentReceived' in order_values and order_values['IsPaymentReceived'] == True:
            payment_status = 'complete'
            acqurer_name = "{} {}".format(marketplace_list_id.name, tradevine_lookup.get_payment_type(
                order_values['PaymentType']))

        return {
            'name': order_values['OrderNumber'],
            'date_order': dateutil.parser.parse(order_values['CompletedDate']).strftime("%Y-%m-%d %H:%M:%S") if order_values.get('CompletedDate') else fields.Datetime.now(),
            'partner_id': customer.id,
            'order_line': self._prepare_order_line_values(config, order_values.get('SalesOrderLines', [])),
            'company_id': self.env.company.id,
            'origin': tradevine_lookup.get_order_origin(order_values['OrderOrigin']),
            'team_id': config.team_id.id,
            'commitment_date': dateutil.parser.parse(order_values['RequestedShippingDate']).strftime("%Y-%m-%d") if order_values.get('RequestedShippingDate') else False,
            'currency_id': currency.id if currency else self.env.company.currency_id.id,
            'warehouse_id': warehouse.id,
            'partner_invoice_id': invoice_address.id or customer.id,
            'partner_shipping_id': shipping_address.id or customer.id,
            'marketplace_name' : marketplace_list_id.id,
            'client_order_ref' : cus_mar_ref,
            'backend_id' : woo_backend.id or False,
            'payment_status': payment_status,
            'acqurer_name': acqurer_name,
        }





# Product for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _load_tradevine_product_for_odoo(self, provider_config, pageNumber=1, pageSize=499):
        response = self._get_tradevine_product_by_paged_list(
            provider_config, pageNumber, pageSize) or {}
        total_product = response.get('TotalCount')
        
        load_product = 0
        product_obj = self.env['product.product']
        marketplace_product_obj = self.env['marketplace.product.template']
        uom = self.env['uom.uom']
        check_barcode_duplicate = []
        while True:
            product_values = []
            if response.get('List') and (total_product - load_product) > 0:
                for product in response['List']:
                    ProductID = product.get('ProductID')
                    domain = [
                        ('marketplace_config_ids.ref_code', '=', ProductID)]
                    if product.get('Barcode'):
                        check_barcode_duplicate.append(product['Barcode'])
                        domain = expression.OR(
                            [domain, [('barcode', '=', product['Barcode'])]])
                    if not product_obj.search(domain, limit=1):
                        vals = self._prepare_product_values(product, provider_config)
                        if vals.get('barcode') in check_barcode_duplicate or not product.get('Barcode'):
                            vals.pop('barcode')

                        marketplace_order = marketplace_product_obj.search(
                            [('ref_code', '=', ProductID)], limit=1)
                        if vals:
                            if product.get('UnitOfMeasure'):
                                uom = uom.search(
                                    [('name', '=', product['UnitOfMeasure'])], limit=1)
                                if uom:
                                    vals.update({'uom_id': uom.id})
                            if not marketplace_order:
                                vals.update({
                                    'marketplace_config_ids': [(0, 0, {
                                        'name': provider_config.name,
                                        'config_id': provider_config.id,
                                        'category_ref_id': product.get('ProductCategoryID'),
                                        'ref_code': ProductID,
                                    })]
                                })
                            else:
                                vals.update({'marketplace_config_ids': [
                                            (4, marketplace_order.id)]})

                            product_values.append(vals)
                if product_values:
                    product_obj.create(product_values)
                    product_obj.env.cr.commit()

                load_product += len(response['List'])
                if load_product != total_product:
                    pageNumber += 1
                    response = self._get_tradevine_product_by_paged_list(
                        provider_config, pageNumber, pageSize) or {}
            else:
                break
        return response




#Order for odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _load_tradevine_order_for_odoo(self, provider_config, pageNumber=1, pageSize=499, createdFrom=None, createdTo=None):
        response = self._get_tradevine_order_by_paged_list(
            provider_config, pageNumber, pageSize, createdFrom=createdFrom, createdTo=createdTo) or {}
        total_order = response.get('TotalCount')
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
                _logger.warning('Tradevine Order values {}'.format(order_values))
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
                    response = self._get_tradevine_order_by_paged_list(
                        provider_config, pageNumber, pageSize, createdFrom=createdFrom, createdTo=createdTo) or {}
            else:
                break
        return response





# Category for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _import_category_from_tradevine(self, config, datas, level=0):
        categories = [{
            'name': datas['Name'],
            'parent_id': False,
            'parent_number': False,
            'marketplace_catg_ref_number': datas['Number'],
            'marketplace_path': datas['Path'],
            'marketplace_config_id': config.id,
        }]

        def get_subcategories(subcategory, parent_name, parent_number, level):
            res = []
            for data in subcategory:
                res.append({
                    'name': data.get('Name'),
                    'parent_id': parent_name,
                    'parent_number': parent_number,
                    'marketplace_catg_ref_number': data.get('Number'),
                    'marketplace_path': data.get('Path'),
                    'marketplace_config_id': config.id,
                })
                if not data['IsLeaf']:
                    res.extend(get_subcategories(
                        data['Subcategories'], data['Name'], data['Number'], level+1))
            return res

        categories.extend(get_subcategories(
            datas['Subcategories'], datas['Name'], datas['Number'], 1))
        records = self.env['marketplace.product.category']
        for categ in categories:
            parent = records.search([('marketplace_catg_ref_number', '=', categ.get(
                'parent_number')), ('name', '=', categ.get('parent_id'))])
            if parent:
                categ['parent_id'] = parent.id
            categ.pop('parent_number')
            records |= records.create(categ)


    def _load_tradevine_category_for_odoo(self, provider_config):
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='https://api.trademe.co.nz/v1/Categories.json',
            params={},
            data={},
            public_service_endpoint=True
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            self._import_category_from_tradevine(provider_config, resp)
        return resp







# Product Photo Post Data >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_photo_post_data(self, provider_config, product, photoID=None):
        _logger.warning('taradevine product {}, {}, PhotoID {}'.format(product._name, product.id, photoID))
        photos = []
        if product.image_1920:
            image = {
                "FileName": "{}_{}.jpeg".format(product.default_code or product.x_studio_sku, random.randrange(10000,100000)),
                "ContentsBase64": product.image_1920.decode('utf-8'),
            }
            resp = self.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=provider_config,
                http_method='POST',
                service_endpoint='v1/Photo/%s' % photoID if photoID else 'v1/Photo',
                params={},
                data=json.dumps(image),
            )
            if isinstance(resp, dict) and not resp.get('error_message'):
                image.update({
                    'PhotoID': resp.get('PhotoID')
                })
                product.marketplace_photo_id = resp.get('PhotoID')
                photos.append(image)
            time.sleep(1)

        return photos




# Product Post data >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_post_data(self, provider_config, product, create_on_tradevine=False):
        _logger.warning('tradevine Product model %s, %i' %
                     (product._name, product.id))
        _logger.warning('tradevine provider_config %s, %i' %
                     (provider_config._name, provider_config.id))
        currency = self.env['res.currency']
        marketplace_brand = self.env['marketplace.product.brand']
        currency_code = False
        if product.currency_id:
            currency_code = tradevine_lookup.get_currency(
                value=product.currency_id.name)
        Photos = self._prepare_product_photo_post_data(
            provider_config, product, product.marketplace_photo_id)
        product_new_price = provider_config.pricelist_id.get_product_price_marketplace(
            product) if provider_config.pricelist_id else None
        taxes_id = product.taxes_id
        if not taxes_id:
            taxes_id = self.env['account.tax'].sudo().search([['id','=',2]])
            product.taxes_id = [(4,taxes_id.id)]
        res = taxes_id.compute_all(product_new_price or product.list_price)
        photo_identifier = ','.join([photo['FileName'] for photo in Photos])
        product.photo_identifier = photo_identifier
        values = {
            'Name': product.name or product.display_name,
            'Code': product.default_code or '',
            'Barcode': product.barcode or '',      
            'Weight': float(product.weight * 1000),
            'Length': float(product.length) * 10,
            'Width' : float(product.width) * 10,
            'Height' : float(product.height) * 10,
            'Currency': currency_code,
            'CostPrice':product.standard_price,
            'Labels': product.display_name or '',
            'EnableInventory': True,
            'MinimumStockQuantity': 0,
            'UnitOfMeasure': product.uom_name,
            'SellPriceIncTax': round(res['total_included'],2),
            'SellPriceExTax': round(res['total_excluded'],2),
            'Brand': product.marketplace_brand_id.name,
            'IsArchived': not product.active,
            'IsBoM': False,
            'IsBoMComponent': False,
            'Photos': Photos,
            'PhotoIdentifier': photo_identifier,
            'OverrideSalesGLAccountCode': '200',
            'OverrideSalesGLAccountName': 'Sales',
            'OverridePurchaseGLAccountCode': '630',
            'OverridePurchaseGLAccountName': 'Inventory',
        }
        
        ConfigApp = product.mapped('marketplace_config_ids').filtered(
            lambda config: config.config_id == provider_config)
        ProductID = ConfigApp.ref_code if ConfigApp else False
        
        if not ProductID:
            values.update({
            'Description': """{}""".format( html2text.html2text(product.description_sale)[:2000] or ''),  
            'InternalNotes':"""{}""".format( html2text.html2text(product.description_sale)[:2000] or ''),
            'ExternalNotes': """{}""".format( html2text.html2text(product.description_sale)[:2000] or ''),
            })

        
        qty = self.get_stock_qtys(product, provider_config)        
        
        if create_on_tradevine:
            values.update({
                'QuantityInStock': qty,
                'QuantityAvailableToSell': qty,
                'QuantityAvailableToShip': qty,
            })

        return values




# Stock Quantity >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def get_stock_qtys(self, product, provider_config):
        qty = 0
        if provider_config.location_ids:
            for loc in provider_config.location_ids:
                qty += sum(product.sudo().with_context({'location' : loc.id}).mapped('free_qty')) if product._name == 'product.product' else sum(product.product_variant_id.sudo().with_context({'location' : loc.id}).mapped('free_qty'))
        if isinstance(qty, (list,tuple)):
            qty = qty[0]

        return qty




# Product Update Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_update_vals(self, provider_config, config_app, product, resp):
        if config_app:
            value = {
                'category_ref_id': resp.get('ProductCategoryID'),
                'ref_code': resp.get('ProductID'),
            }
            stock_qtys = self.get_stock_qtys(product, provider_config)
            if product._name == 'product.template':
                value.update(
                    {'product_template_qty': stock_qtys})
            else:
                value.update({'product_qty': stock_qtys})
            return config_app.write(value)
        else:
            return self.env['marketplace.product.template'].create({
                'name': provider_config.api_provider,
                'ref_code': resp.get('ProductID'),
                'config_id': provider_config.id,
                'product_template_id': product.id if product._name == 'product.template' else False,
                'product_id': product.id if product._name == 'product.product' else product.product_variant_id.id,
                'category_ref_id': resp.get('ProductCategoryID'),
            })







# trade me listing rule >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _post_trade_me_listing_rule(self, provider_config,  product, resp={}, config_app=False, params=None):
        if product._name == 'marketplace.product.template':
            product = product.product_template_id


        for rule in product.trade_me_listing_rule_ids.filtered(lambda r: r.config_id.id == provider_config.id):            
            qty = self.get_stock_qtys(product, provider_config)
            buy_now_qty = rule.buy_now_max_qty if rule.buy_now_max_qty != 0 else qty
            data = {
                'TradeMeListingRuleID': rule.ref_code or None,
                'ProductID': resp.get('ProductID') or rule.marketplace_product.ref_code,
                'ProdcutCode': resp.get('Code') or product.default_code or None,
                'RuleName': rule.name,
                'Title': rule.title,
                'SubTitle': rule.subtitle,
                'ExternalTradeMeOrganisationName': rule.external_trade_me_organisation_name,
                'CategoryNumber': rule.category_number.marketplace_catg_ref_number,
                'IsAutoListingEnabled': rule.is_auto_listing_enabled,
                'AutoListingPriority': int(rule.auto_listing_priority),
                'IsUseBuyNow': rule.is_use_buy_now_enabled,
                'Photos': product.marketplace_photo_id or None,
                'PhotoIdentifier': product.photo_identifier or None,
                'BuyNowPrice': rule.buy_now_price,
                "IsSellMultipleQty": bool(buy_now_qty),
                "SellMultipleQuantity": buy_now_qty,
                'StartPrice': round(rule.buy_now_price if rule.is_use_buy_now_enabled else rule.start_price, 2),
                'IsListingNew': rule.is_listing_new,

            }
            if not rule.ref_code:
                data.update({
                'Description':html2text.html2text(product.description_sale)[:2000] or '',
                })
                
            _logger.warning('_post_trade_me_listing_rule data {}'.format(data))
            resp = self.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=provider_config,
                http_method='POST',
                service_endpoint='v1/TradeMeListingRule/%s' % rule.ref_code if rule.ref_code else 'v1/TradeMeListingRule/',
                params=params or {},
                data=json.dumps(data),
            )

            if isinstance(resp, dict) and not resp.get('error_message'):
                rule.ref_code = resp.get('TradeMeListingRuleID')
            time.sleep(1)

    def _temp_update_self(self, provider_config, ConfigApp, product, data, ProductID=None):
        if ProductID:
            data.update({'ProductID': ProductID})
            if product._name == 'product.product':
                if ConfigApp.product_qty > product.free_qty:
                    self = self.with_context(
                        reduce_stock_qty=ConfigApp.product_qty - product.free_qty)
                else:
                    self = self.with_context(
                        increase_stock_qty=product.free_qty - ConfigApp.product_qty)
                if product.free_qty != ConfigApp.product_qty:
                    self._update_tradevine_product_stock(
                        provider_config, product, product.warehouse_id)
            else:
                if ConfigApp.product_template_qty > product.virtual_available:
                    self = self.with_context(
                        reduce_stock_qty=ConfigApp.product_template_qty - product.virtual_available)
                else:
                    self = self.with_context(
                        increase_stock_qty=product.virtual_available - ConfigApp.product_template_qty)
                if product.virtual_available != ConfigApp.product_template_qty:
                    self._update_tradevine_product_stock(
                        provider_config, product, product.warehouse_id)
            return self
        return self

    def _post_tradevine_product(self, provider_config, product, config_field, params=None):
        ConfigApp = product.mapped('%s' % config_field).filtered(
            lambda config: config.config_id == provider_config)
        ProductID = ConfigApp.ref_code if ConfigApp else False
        data = self._prepare_product_post_data(
            provider_config, product, create_on_tradevine=not bool(ProductID))

        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='v1/Product/%s' % ProductID if ProductID else 'v1/Product',
            params=params or {},
            data=json.dumps(data),
        )

        if isinstance(resp, dict) and not resp.get('error_message'):
            self._prepare_product_update_vals(
                provider_config, ConfigApp, product, resp)
            self._update_tradevine_product_stock(
                provider_config, product, provider_config.location_ids)
            self._post_trade_me_listing_rule(
                provider_config, product, resp, ConfigApp)
            
           
        return resp

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

    def _post_tradevine_sale_order(self, provider_config, order, config_field, params=None):
        ConfigApp = order.mapped('%s' % config_field)
        SaleOrderID = ConfigApp.ref_code
        data = self._prepare_sale_order_post_data(provider_config, order)
        if SaleOrderID:
            data.update({'SalesOrderID': SaleOrderID})
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='v1/SalesOrder/%s' % SaleOrderID if SaleOrderID else 'v1/SalesOrder',
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

    def _delete_tradevine_listing_rule(self, rule):
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=rule.config_id,
            http_method='POST',
            service_endpoint='v1/TradeMeListingRule/DeleteRule/%s' % rule.ref_code,
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            return True
        if isinstance(resp, dict) and resp.get('error_message'):
            raise UserError(_("Error! %s" % resp.get('error_message')))
        rule.ref_code = False
        return True

    # ============================================================
    # UPDATE PRODUCT STOCK WHEN SALE ORDER CONFIRM DIRECT BY ODOO
    # ============================================================

    def _prepare_product_post_stock_data(self, ConfigApp, product, location_ids=False, sale_order=False, default_type=None):
        inventory_entry = tradevine_lookup.get_inventory_entry_type(
            default_type)


        if sale_order:
            default_type = 36009
            qty = 0 
            for loc in location_ids:
                qty += sum(product.with_context({"location" : loc.id}).mapped("free_qty")) if product._name == 'product.product' else sum(product.product_variant_id.sudo().with_context({'location' : loc.id}).mapped('free_qty'))

            inventory_adjustment_note = _(
                'Odoo Increase/Reduce Stock Product Inventory due to sale order %s' % qty)
                
            
        else:
            default_type = 36009
            qty = 0 
            for loc in location_ids:
                qty += sum(product.with_context({"location" : loc.id}).mapped("free_qty")) if product._name == 'product.product' else sum(product.product_variant_id.sudo().with_context({'location' : loc.id}).mapped('free_qty'))
            
            inventory_adjustment_note = _(
                'Odoo Increase/Reduce Stock Product Inventory %s' % qty)

        if isinstance(qty, (list, tuple)):
            qty = qty[0]

        _logger.warning("Quantity Found of {} : {}; location_id {} quantity {}".format(product._name, product.id,location_ids.ids, qty))
        
        values = {
            'ProductID': ConfigApp.ref_code,
            'ProductCode': product.code if product._name == 'product.product' and product.code else None,
            'InventoryType': default_type,
            # 'QuantityChange': qty if sale_order else None,
            'QuantityChange': None,
            'ProductCostPrice': product.standard_price,
            # 'QuantityInStockSnapshot': None if sale_order else qty,
            'QuantityInStockSnapshot' : qty,
            'Notes': sale_order.inventory_adjustment_note if sale_order and sale_order.inventory_adjustment_note else inventory_adjustment_note,
            'WarehouseID': None,
            'WarehouseCode': None,
            'TransferFromWarehouseID': None,
            'TransferFromWarehouseCode': None,
            'TransferToWarehouseID': None,
            'TransferToWarehouseCode': None,
            'QueueInventorySummaryUpdates': None
        }
        return values

    def _update_tradevine_product_stock(self, config, product, location_ids=False, sale_order=False, params=None):
        ConfigApp = product.mapped('marketplace_config_ids').filtered(
            lambda m_config: m_config.config_id == config and m_config.ref_code)
        ProductID = ConfigApp.mapped("ref_code")[-1] if ConfigApp else False
        _logger.warning("Updating stock of {} : {} ref {}".format(product._name, product.id, ProductID))
        if ProductID:
            data = self._prepare_product_post_stock_data(
                ConfigApp, product, location_ids, sale_order)
            data.update({'ProductID': ProductID})

            _logger.warning("Tradevine ProductInventory MakeAdjustment body {}".format(json.dumps(data)))
            resp = self.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=config,
                http_method='POST',
                service_endpoint='v1/ProductInventory/%s/MakeAdjustment' % ProductID,
                params=params or {},
                data=json.dumps(data),
            )
            if isinstance(resp, dict) and not resp.get('error_message'):
                self._prepare_product_update_vals(
                    config, ConfigApp, product, resp)
            return resp
        return {'error_message': _('Product ID is missing for tradevine stock adjustment')}

    def cron_fetch_online_sale_order_tradevine(self, config_app):
        current_date = fields.Datetime.from_string(
            fields.Date.context_today(self))
        tradevine_tz = pytz.timezone(config_app.tz or 'UTC')
        
        start_with_zero_hours = current_date.astimezone(
            tradevine_tz).replace(tzinfo=None)
        
        createdFrom = current_date.replace(
            hour=0, minute=0, second=0, microsecond=0)- timedelta(days=7)

        createdTo = current_date.astimezone(
            tradevine_tz).replace(tzinfo=None)
        
        createdFrom = '{:%Y-%m-%dT%H:%M:%S.%fz}'.format(createdFrom)
        createdTo = '{:%Y-%m-%dT%H:%M:%S.%fz}'.format(createdTo)
        
        return self._load_tradevine_order_for_odoo(
            config_app, pageNumber=1, pageSize=499, createdFrom=createdFrom, createdTo=createdTo)
