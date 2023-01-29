# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import count
import pprint
import pytz
import json
import logging
import requests
import time
import uuid
import urllib.parse
import dateutil.parser
import datetime
import html2text

from werkzeug.urls import url_quote

from odoo import fields, models, _
from odoo.osv import expression

from odoo.exceptions import UserError

from ...marketplace_connector.models import themarket_lookup

_logger = logging.getLogger(__name__)


class TheMarket(models.AbstractModel):
    _name = 'themarket'
    _description = 'TheMarket API'
    # merchantid = fields.Integer("Merchant Id", store =False)
    # userkey = fields.Char("User Key", store =False)
    # token = fields.Char("Bearer Token", store =False)

    def _get_themarket_api_auth(self, provider_config):
        if provider_config.api_provider == 'themarket':
            params = {
                'Username': provider_config.themarket_username,
                'Password': provider_config.themarket_password
            }
            response = requests.request(
                'POST', provider_config.api_url + '/api/auth/login',
                params=params,
                timeout=20).json()

            if response.get('AppCode'):
                raise Warning(response.get('AppCode'))
            else:
                provider_config.themarket_userkey = response.get('UserKey')
                provider_config.themarket_token = response.get('Token')
                # self._get_themarket_user_info(provider_config)
        return provider_config

    def _get_themarket_user_info(self, provider_config):
        if provider_config.api_provider == 'themarket':
            if not provider_config.themarket_userkey:
                provider_config = self._get_themarket_api_auth(provider_config)

            params = {
                'userkey': provider_config.themarket_userkey,
                'cc': 'EN'
            }
            headers = self._get_themarket_oauth_header(provider_config)

            response = requests.request(
                'GET',
                provider_config.api_url + '/api/user/view',
                headers=headers,
                params=params,
            ).json()

            if response.get('AppCode'):
                raise Warning(response.get('AppCode'))
            else:
                provider_config.themarket_merchantid = response.get(
                    'MerchantId')
        return provider_config

    def _get_themarket_oauth_header(self, api_provider_config):

        if not api_provider_config.themarket_userkey and not api_provider_config.themarket_token:
            api_provider_config = self._get_themarket_api_auth(
                api_provider_config)

        header_oauth = 'Bearer ' + api_provider_config.themarket_token
        headers = {
            'Authorization': header_oauth,
            'Content-Type': 'application/json',
        }
        return headers

    def _get_themarket_product_by_id(self, provider_config, style_code, **kwargs):
        '''This method gets an individual product specified by the supplied ID - 
            the output consists of top level product information, including summary inventory quantities
        '''
        if provider_config.themarket_merchantid == 0 \
                or provider_config.write_date < (fields.Datetime.now() - datetime.timedelta(hours=72)):
            provider_config = self._get_themarket_user_info(provider_config)

        params = {
            'cc': 'EN',
            'merchantid': provider_config.themarket_merchantid,
            'stylecode': style_code,
        }

        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/product/style/view' % style_code,
            params={},
            data={},
        )

    def _get_themarket_product_by_paged_list(self, provider_config, pageNumber=1, pageSize=50, **kwargs):
        ''' This method gets a paged list of top level product information, including summary inventory quantities. '''
        if provider_config.themarket_merchantid == 0 \
                or provider_config.write_date < (fields.Datetime.now() - datetime.timedelta(hours=72)):
            provider_config = self._get_themarket_user_info(provider_config)

        params = {
            'pageNumber': pageNumber,
            'pageSize': pageSize,
            'merchantid': provider_config.themarket_merchantid,
            'cc': 'EN',
            **kwargs
        }
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/product/style/list',
            params=params,
            data={},
        )

    def _get_themarket_order_by_paged_list(self, provider_config, pageNumber=1, pageSize=50, **kwargs):
        ''' This method gets a paged list of top level product information, including summary inventory quantities. '''
        if provider_config.themarket_merchantid == 0 \
                or provider_config.write_date < (fields.Datetime.now() - datetime.timedelta(hours=72)):
            provider_config = self._get_themarket_user_info(provider_config)

        params = {
            'pageNumber': pageNumber,
            'pageSize': pageSize,
            'merchantid': provider_config.themarket_merchantid,
            'cc': 'EN',
            **kwargs
        }
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/order/list',
            params=params,
            data={},
        )

    def _get_themarket_product(self, provider_config, product_id=None, **kwargs):
        if product_id:
            return self._get_themarket_product_by_id(provider_config, product_id, **kwargs)
        if not product_id:
            return self._get_themarket_product_by_paged_list(provider_config, **kwargs)



    def _prepare_product_values(self, product_values):
        currency = self.env['res.currency']
        marketplace_brand = self.env['marketplace.product.brand']
        if product_values.get('Currency'):
            currency_name = themarket_lookup.get_currency(
                product_values['Currency'])
            currency = currency.search([('name', '=', currency_name)], limit=1)
        if product_values.get('BrandId'):
            marketplace_brand = marketplace_brand.search(
                [('ref_code', '=', product_values['BrandId'])], limit=1)
            if not marketplace_brand:
                marketplace_brand = marketplace_brand.create(
                    {'name': product_values['SourceBrandCode'], 'ref_code': product_values['BrandId']})

        return {
            'name': product_values['SkuName'].replace(",", "-"),
            'code': product_values['StyleCode'],
            'barcode': product_values.get('SkuList')[0]['Barcode'],
            'description': str(product_values.get('SkuDesc')),
            'description_sale': str(product_values.get('SkuDesc')),
            'default_code': product_values.get('StyleCode'),
            'standard_price': product_values.get('PriceRetail'),
            'lst_price': product_values.get('PriceRetail'),
            'list_price': product_values.get('PriceRetail'),
            'weight': product_values.get('ShippingWeight'),
            'currency_id': currency.id,
            'marketplace_brand_id': marketplace_brand.id if marketplace_brand else product_values.get('SourceBrandCode'),
            'active': True if product_values.get('StatusId') == 2 else False,
            'marketplace_enable_inventory': True if product_values.get('SkuList')[0]['InventoryStatusId'] == 2 else False,
            # 'category_ref_id': product_values.get('ProductCategoryID'),
        }

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
                        'need_to_create_address', True))._create_new_themarket_customer_values(values, parent)
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

    def _create_new_themarket_customer_values(self, values, parent=False):
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
                state_name = themarket_lookup.get_regions_and_states(
                    address['RegionState'])
                state = state.search([('name', '=', state_name)], limit=1)
            if address.get('Country'):
                country_name = themarket_lookup.get_country(address['Country'])
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
                    state_name = themarket_lookup.get_regions_and_states(
                        values['RegionState'])
                    state = state.search([('name', '=', state_name)], limit=1)
                if values.get('Country'):
                    country_name = themarket_lookup.get_country(
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
                    self._prepare_product_values(order_line_value))
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

    def _prepare_order_values(self, config, order_values):
        self = self.with_context(config=config)
        BillingAddress = order_values['BillingAddress']
        ShippingAddress = order_values['ShippingAddress']
        if BillingAddress:
            BillingAddress.update({'type': 'invoice'})
        if ShippingAddress:
            ShippingAddress.update({'type': 'delivery'})

        customer, invoice_address, shipping_address = self._prepare_customer_values(
            order_values['Customer'], BillingAddress, ShippingAddress)
        currency = self.env['res.currency']
        if order_values['Currency']:
            currency_name = themarket_lookup.get_currency(
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
            'origin': themarket_lookup.get_order_origin(order_values['OrderOrigin']),
            'team_id': config.team_id.id,
            'commitment_date': dateutil.parser.parse(order_values['RequestedShippingDate']).strftime("%Y-%m-%d") if order_values.get('RequestedShippingDate') else False,
            'currency_id': currency.id if currency else self.env.company.currency_id.id,
            'warehouse_id': warehouse.id,
            'partner_invoice_id': invoice_address.id or customer.id,
            'partner_shipping_id': shipping_address.id or customer.id,
        }










    def _load_themarket_product_for_odoo(self, provider_config, pageNumber=1, pageSize=50):
        response = self._get_themarket_product_by_paged_list(
            provider_config, pageNumber, pageSize) or {}
        total_product = response.get('HitsTotal')
        load_product = 0
        product_obj = self.env['product.product']
        marketplace_product_obj = self.env['marketplace.product.template']
        uom = self.env['uom.uom']
        check_barcode_duplicate = []
        while True:
            product_values = []
            if response.get('PageData') and (total_product - load_product) > 0:
                for product in response['PageData']:
                    _logger.info("The market Product Style code: {}".format(
                        product['StyleCode']))
                    ProductID = product.get('StyleCode')
                    domain = [
                        ('marketplace_config_ids.ref_code', '=', ProductID)]
                    bracode = product.get('SkuList')[0]['Barcode']
                    # _logger.info("The Market Product Barcode: {}".format(bracode))
                    if bracode:
                        check_barcode_duplicate.append(bracode)
                        domain = expression.OR(
                            [domain, [('barcode', '=', bracode)]])
                    # _logger.info("The Market product_obj by barcode: {}".format(product_obj.search(domain, limit=1)))
                    if not product_obj.search(domain, limit=1):
                        vals = self._prepare_product_values(product)
                        _logger.info(
                            "The Market Product values: {}".format(vals))
                        if vals.get('barcode') in check_barcode_duplicate or not bracode:
                            vals.pop('barcode')

                        marketplace_order = marketplace_product_obj.search(
                            [('ref_code', '=', ProductID)], limit=1)
                        catIds = []
                        if vals:
                            if product.get('UnitOfMeasure'):
                                uom = uom.search(
                                    [('name', '=', product['UnitOfMeasure'])], limit=1)
                                if uom:
                                    vals.update({'uom_id': uom.id})

                            if product.get('CategoryPriorityList'):
                                for categ in product.get('CategoryPriorityList'):
                                    catIds.append(categ.get('CategoryId'))

                            if not marketplace_order:
                                vals.update({
                                    'marketplace_config_ids': [(0, 0, {
                                        'name': provider_config.name,
                                        'config_id': provider_config.id,
                                        'category_ref_id': catIds[-1] if len(catIds) > 0 else None,
                                        'ref_code': ProductID,
                                    })]
                                })
                            else:
                                vals.update({'marketplace_config_ids': [
                                            (4, marketplace_order.id)]})

                            product_values.append(vals)
                if product_values:
                    _logger.info("Product values : {}".format(product_values))
                    product_obj.create(product_values)
                    product_obj.env.cr.commit()

                load_product += len(response['PageData'])
                if load_product != total_product:
                    pageNumber += 1
                    response = self._get_themarket_product_by_paged_list(
                        provider_config, pageNumber, pageSize) or {}
                    break
            else:
                break
        return response




    def _load_themarket_order_for_odoo(self, provider_config, pageNumber=1, pageSize=499, createdFrom=None, createdTo=None):
        response = self._get_themarket_order_by_paged_list(
            provider_config, pageNumber, pageSize, createdFrom=createdFrom, createdTo=createdTo) or {}
        total_order = response.get('HitsTotal')
        load_order = 0
        sale_order_obj = self.env['sale.order']
        marketplace_order_obj = self.env['marketplace.order']
        while True:
            order_values = []
            if response.get('PageData') and (total_order - load_order) > 0:
                for order in response['PageData']:
                    SalesOrderID = order.get('OrderKey')
                    domain = [
                        ('marketplace_config_id.ref_code', '=', SalesOrderID)]
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

                if order_values:
                    saleOrders = sale_order_obj.create(order_values)
                    for saleOrder in saleOrders:
                        saleOrder.marketplace_config_id.sale_order_ref = saleOrder.name

                    sale_order_obj.env.cr.commit()

                load_order += len(response['List'])
                if load_order != total_order:
                    pageNumber += 1
                    response = self._get_themarket_order_by_paged_list(
                        provider_config, pageNumber, pageSize, createdFrom=createdFrom, createdTo=createdTo) or {}
            else:
                break
        return response

    def _import_category_from_themarket(self, config, datas, level=0):
        
        categories = [{
        'name': datas['CategoryName'],
        'parent_id': False,
        'parent_number': False,
        'marketplace_catg_ref_number': datas['CategoryId'],
        'marketplace_path': datas['CategoryCode'],
        'marketplace_config_id': config.id,
        }]

        def get_subcategories(subcategory, parent_name, parent_number, level):
            res = []
            for sub in subcategory:
                _logger.info('Fetching : {}/{}'.format(parent_name, sub.get('CategoryName')))
                res.append({
                    'name': sub.get('CategoryName'),
                    'parent_id': parent_name,
                    'parent_number': parent_number,
                    'marketplace_catg_ref_number': sub.get('CategoryId'),
                    'marketplace_path': sub.get('CategoryCode'),
                    'marketplace_config_id': config.id,
                })
                if not len(sub['CategoryList']) == 0:
                    res.extend(get_subcategories(
                        sub['CategoryList'], sub['CategoryName'], sub['CategoryId'], level+1))
            return res

        categories.extend(get_subcategories(
            datas['CategoryList'], datas['CategoryName'], datas['CategoryId'], 1))
        records = self.env['marketplace.product.category']
        for categ in categories:
            # _logger.info('inserting : {}/{}'.format(categ.get('parent_id'), categ.get('name')))
            category = records.search([('marketplace_catg_ref_number', '=',categ.get('marketplace_catg_ref_number') )], limit=1)
            
            parent = records.search([('marketplace_catg_ref_number', '=', categ.get(
                'parent_number')), ('name', '=', categ.get('parent_id'))], limit=1)
            if parent:
                categ['parent_id'] = parent.id
            categ.pop('parent_number')
            # _logger.info('categ : {}'.format(categ))
            if not bool(category):
                category = records.create(categ)
            else: 
                category.write(categ)
            self._cr.commit()

    def _load_themarket_category_for_odoo(self, provider_config):
        params = {
            "cc":"EN",
            "showAll":"true"
        }

        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/category/list',
            params=params,
            data={}
        )
        _logger.info("_load_themarket_category_for_odoo {}".format(resp))
        if isinstance(resp, list):
            for data in resp:
                self._import_category_from_themarket(provider_config, data)
        return resp

    def _load_themarket_brands_for_odoo(self, provider_config):
        params = {
            'cc':'EN',
            'lite':1,
            'merchantid':provider_config.themarket_merchantid,
            'showallbrands':1
        }

        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/brand/list',
            params=params,
            data={}
        )
        _logger.info("_load_themarket_category_for_odoo {}".format(resp))
        marketplace_brand = self.env['marketplace.product.brand']
        if isinstance(resp, list):
            for data in resp:
                _logger.info("Brand Name {} Brand ID {}".format( data.get('BrandName'),data.get('BrandId')))
                res = {
                        "name": data.get('BrandName'),
                        "config_id":provider_config.id,
                        "ref_code": data.get('BrandId')
                    }
                brand = marketplace_brand.search([('ref_code','=',data.get('BrandId'))], limit=1)
                if not bool(brand):
                    brand = marketplace_brand.create(res)
                else:
                    brand.write(res)
                
                self._cr.commit()
                _logger.info("Marketplace Brand ID : {}, {}".format(brand.id, brand.name))
                
        return resp

    def _load_themarket_colors_for_odoo(self, provider_config):
        params = {
            'cc':'EN',
            'Showall':1
        }

        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/color/list',
            params=params,
            data={}
        )
        _logger.info("_load_themarket_colors_for_odoo {}".format(resp))
        themarket_color = self.env['themarket.color.mapping']
        if isinstance(resp, list):
            for data in resp:
                _logger.info("Color Name {} color ID {}".format( data.get('ColorName'),data.get('ColorId')))
                res = {
                        "name": data.get('ColorName'),
                        "themarket_ref": data.get('ColorId'),
                        "themarket_color_code" : data.get('ColorCode'),
                    }
                color = themarket_color.search([('themarket_ref','=',data.get('ColorId'))], limit=1)
                if not bool(color):
                    color = themarket_color.create(res)
                else:
                    color.write(res)
                
                self._cr.commit()
                _logger.info("Marketplace Color ID : {}, {}".format(color.id, color.name))
        else : 
            _logger.error("Error in Themarket color api : {}".format(resp))
                
        return resp

    def _post_themarket_product_image(self, provider_config,image_name, image):
        _logger.info('TheMaket Uploading photo')
        files = [(
            'file',(
                image_name  ,
                image.decode('utf-8'),
                'image/jpeg'
                )
            )]
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='api/image/upload',
            params={"b":"productimages"},
            files = files,
        )

        

    def _prepare_product_post_data(self, provider_config, product, create_on_themarket=False):
        _logger.info('themarket Product model %s, %i' %
                     (product._name, product.id))
        _logger.info('themarket provider_config %s, %i' %
                     (provider_config._name, provider_config.id))
        currency = self.env['res.currency']
        marketplace_brand = self.env['marketplace.product.brand']
        currency_code = False
        if product.currency_id:
            currency_code = themarket_lookup.get_currency(
                value=product.currency_id.name)
        Photos = self._prepare_product_photo_post_data(
            provider_config, product, product.marketplace_photo_id)
        product_new_price = provider_config.pricelist_id.get_product_price_marketplace(
            product) if provider_config.pricelist_id else None
        taxes_id = product.taxes_id
        if not taxes_id:
            taxes_id = self.env.ref('l10n_generic_coa.sale_tax_template')
        res = taxes_id.compute_all(product_new_price or product.list_price)
        photo_identifier = ','.join([photo['FileName'] for photo in Photos])
        product.photo_identifier = photo_identifier
        # for rule in product.trade_me_listing_rule_ids:
        _logger.warning('_prepare_product_post_data description {}'.format( html2text.html2text(product.description) or ''))
        _logger.warning('_prepare_product_post_data description_sale {}'.format( html2text.html2text(product.description_sale) or ''))
        values = {
            "StyleCode": product.default_code,
            "PriceRetail": product_new_price or product.standard_price,
            "BrandId" : 16483,
            "StatusId": 2,
            "SeasonId": 0,
            "BadgeId": 0,
            "GeoCountryId": 0,
            "DisplayRanking": 0,
            "TaxClassId": 1,
            "IsDangerousGoods": 0,
            "IsBulky": 0,
            "IsBrandedImport": 1,
            "IsLocal": 0,
            "IsDeliveryDate": 0,
            "IsOverride": 0,
            "IsClickAndCollect": 1,
            "IsDelivery": 1,
            "IsSoldSeparately": 1,
            "SkuTypeId": 1,
            "ShippingVolume": False,
            "ShippingWeight": 1.5,
            "ShippingWidth": "10",
            "ShippingDepth": "10",
            "ShippingHeight": "5",
            "ShippingSizeId": 0,
            "DeliveryTimeId": 0,
            "ConditionId": 1,
            "WebKey": product.display_name or product.name,
            "MaxBuyQty": 0,
            "IsHideSavings": 0,
            "RestrictSalesChannelId": 0,
            "StyleSkuName": product.display_name or product.name,
            "StyleSkuDesc": html2text.html2text(product.description_sale) or '',
            "ColorImageListMap":"",
            'Name': product.display_name or product.name,
            'Description': html2text.html2text(product.description) or '',
            'Code': product.default_code or '',
            'Barcode': product.barcode or '',
            'InternalNotes': html2text.html2text(product.description) or '',
            'ExternalNotes': html2text.html2text(product.description_sale) or '',
            'Weight': product.weight,
            'Currency': currency_code,
            'CostPrice': product.standard_price,
            'Labels': product.display_name or '',
            'EnableInventory': False,
            'MinimumStockQuantity': 0,
            'UnitOfMeasure': product.uom_name,
            'SellPriceIncTax': round(res['total_included'],2),
            'SellPriceExTax': round(res['total_excluded'],2),
            'Brand': product.marketplace_brand_id.name,
            'IsArchived': not product.active,
            'ColorImageListMap': Photos,
            'OverrideSalesGLAccountCode': '200',
            'OverrideSalesGLAccountName': 'Sales',
            'OverridePurchaseGLAccountCode': '630',
            'OverridePurchaseGLAccountName': 'Inventory',
        }



        if create_on_themarket:
            values.update({
                'QuantityInStock': product.free_qty if product._name == 'product.product' else product.virtual_available,
                'QuantityAvailableToSell': product.free_qty if product._name == 'product.product' else product.virtual_available,
                'QuantityAvailableToShip': product.free_qty if product._name == 'product.product' else product.virtual_available,
            })

        return values

    def _prepare_product_update_vals(self, provider_config, config_app, product, resp):
        if config_app:
            value = {
                'category_ref_id': resp.get('ProductCategoryID'),
                'ref_code': resp.get('ProductID'),
            }
            if product._name == 'product.template':
                value.update(
                    {'product_template_qty': product.virtual_available})
            else:
                value.update({'product_qty': product.free_qty})
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

    def _post_themarket_listing_rule(self, provider_config, config_app, product, resp, params=None):
        for rule in product.trade_me_listing_rule_ids:
            _logger.warning('_post_themarket_listing_rule description{}'.format( html2text.html2text(rule.description) or ''))
            data = {
                'TradeMeListingRuleID': rule.ref_code or None,
                'ProductID': resp.get('ProductID') or rule.marketplace_product.ref_code,
                'ProdcutCode': resp.get('Code') or product.default_code or None,
                'RuleName': rule.name,
                'Title': rule.title,
                'SubTitle': rule.subtitle,
                'ExternalTradeMeOrganisationName': rule.external_trade_me_organisation_name,
                'CategoryNumber': rule.category_number.marketplace_catg_ref_number,
                'Description': html2text.html2text(rule.description) or '',
                'IsAutoListingEnabled': rule.is_auto_listing_enabled,
                'AutoListingPriority': int(rule.auto_listing_priority),
                'IsUseBuyNow': rule.is_use_buy_now_enabled,
                'Photos': product.marketplace_photo_id or None,
                'PhotoIdentifier': product.photo_identifier or None,
                'BuyNowPrice': rule.buy_now_price,
                "IsSellMultipleQty": bool(rule.buy_now_max_qty),
                "SellMultipleQuantity": rule.buy_now_max_qty,
                'StartPrice': rule.buy_now_price if rule.is_use_buy_now_enabled else rule.start_price,
                'IsListingNew': rule.is_listing_new,

            }
            print('_post_trade_me_listing_rule data', data)
            resp = self.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=provider_config,
                http_method='POST',
                service_endpoint='v1/TradeMeListingRule/%s' % rule.ref_code if rule.ref_code else 'v1/TradeMeListingRule/',
                params=params or {},
                data=json.dumps(data),
            )

            if isinstance(resp, dict) and not resp.get('error_message'):
                rule.ref_code = resp.get('TradeMeListingRuleID')

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
                    self._update_themarket_product_stock(
                        provider_config, product, product.warehouse_id)
            else:
                if ConfigApp.product_template_qty > product.virtual_available:
                    self = self.with_context(
                        reduce_stock_qty=ConfigApp.product_template_qty - product.virtual_available)
                else:
                    self = self.with_context(
                        increase_stock_qty=product.virtual_available - ConfigApp.product_template_qty)
                if product.virtual_available != ConfigApp.product_template_qty:
                    self._update_themarket_product_stock(
                        provider_config, product, product.warehouse_id)
            return self
        return self

    def _post_themarket_product(self, provider_config, product, config_field, params=None):
        ConfigApp = product.mapped('%s' % config_field).filtered(
            lambda config: config.config_id == provider_config)
        ProductID = ConfigApp.ref_code if ConfigApp else False
        data = self._prepare_product_post_data(
            provider_config, product, create_on_themarket=not bool(ProductID))
        self = self._temp_update_self(
            provider_config, ConfigApp, product, data, ProductID)
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
            self._post_trade_me_listing_rule(
                provider_config, ConfigApp, product, resp)

            # if bool(product.bom_count):
            #     bom_product_component = []
            #     if product._name == 'product.product':
            #         bom = self.env['mrp.bom'].search(['|', ('product_id', '=', product.id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product.product_tmpl_id.id)])
            #     else:
            #         bom = self.env['mrp.bom'].search([('product_tmpl_id', '=', product.id)])
            #     duplicate = []
            #     for bom_product in bom.bom_line_ids:
            #         if bom_product.product_id not in duplicate:
            #             duplicate.append(bom_product.product_id)
            #             ConfigApp = bom_product.product_id.mapped('%s' % config_field).filtered(lambda config: config.config_id == provider_config)
            #             BomProductID = ConfigApp.ref_code if ConfigApp else False
            #             data = self.with_context(bom_component=True)._prepare_product_post_data(provider_config, bom_product.product_id, create_on_themarket=not bool(BomProductID))
            #             self = self._temp_update_self(provider_config, ConfigApp, bom_product.product_id, data, BomProductID)
            #             bom_component_resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            #                 api_provider_config=provider_config,
            #                 http_method='POST',
            #                 service_endpoint='v1/Product/%s' % BomProductID if BomProductID else 'v1/Product',
            #                 params=params or {},
            #                 data=json.dumps(data),
            #             )
            #             if isinstance(bom_component_resp, dict) and not bom_component_resp.get('error_message'):
            #                 bom_product_component.append((bom_component_resp.get('ProductID'), bom_component_resp.get('Code'), bom_product.product_qty))
            #                 self._prepare_product_update_vals(provider_config, ConfigApp, bom_product.product_id, bom_component_resp)
            #                 data = [{
            #                     'BoMComponentProductID': component[0],
            #                     'BoMComponentProductCode': component[1],
            #                     'BoMComponentQuantity': component[2],
            #                 } for component in bom_product_component]

            #                 self.env['marketplace.connector']._synch_with_marketplace_api(
            #                     api_provider_config=provider_config,
            #                     http_method='POST',
            #                     service_endpoint='v1/Product/SaveBoMComponents/%s' % resp.get('ProductID'),
            #                     params=params or {},
            #                     data=json.dumps(data),
            #                 )
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

    def _post_themarket_sale_order(self, provider_config, order, config_field, params=None):
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

    def _delete_themarket_listing_rule(self, rule):
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

    def _prepare_product_post_stock_data(self, ConfigApp, product, warehouse, sale_order=False, default_type=None):
        inventory_entry = themarket_lookup.get_inventory_entry_type(
            default_type)
        increase_stock_qty = self.env.context.get('increase_stock_qty')
        reduce_stock_qty = self.env.context.get('reduce_stock_qty')
        if (sale_order and sale_order.state == 'cancel'):
            default_type = 36014
            qty = +sum(sale_order.order_line.filtered(lambda line: line.product_id ==
                       product).mapped('product_uom_qty')),
            inventory_adjustment_note = _(
                'Increase Stock Product Inventory due to sale order')
        elif (sale_order and sale_order.state != 'cancel'):
            default_type = 36015
            qty = -sum(sale_order.order_line.filtered(lambda line: line.product_id ==
                       product).mapped('product_uom_qty')),
            inventory_adjustment_note = _(
                'Reduce Stock Product Inventory due to sale order')
        elif not sale_order and (increase_stock_qty or reduce_stock_qty):
            default_type = 36009
            qty = product.free_qty if product._name == 'product.product' else product.virtual_available,
            inventory_adjustment_note = _(
                'Increase/Reduce Stock Product Inventory %s' % qty)
        values = {
            'ProductID': ConfigApp.ref_code,
            'ProductCode': product.code if product._name == 'product.product' and product.code else None,
            'InventoryType': default_type,
            'QuantityChange': qty if sale_order else None,
            'ProductCostPrice': product.standard_price,
            'QuantityInStockSnapshot': None if sale_order else product.free_qty if product._name == 'product.product' else product.virtual_available,
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

    def _update_themarket_product_stock(self, config, product, warehouse, sale_order=False, params=None):
        ConfigApp = product.mapped('marketplace_config_ids').filtered(
            lambda m_config: m_config.config_id == config)
        ProductID = ConfigApp.ref_code if ConfigApp else False
        if ProductID:
            data = self._prepare_product_post_stock_data(
                ConfigApp, product, warehouse, sale_order)
            data.update({'ProductID': ProductID})
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
        return {'error_message': _('Product ID is missing for themarket stock adjustment')}

    def cron_fetch_online_sale_order_themarket(self, config_app):
        current_date = fields.Datetime.from_string(
            fields.Date.context_today(self))
        themarket_tz = pytz.timezone(config_app.tz or 'UTC')
        start_with_zero_hours = current_date.astimezone(
            themarket_tz).replace(tzinfo=None)
        createdFrom = current_date.replace(
            hour=0, minute=0, second=0, microsecond=0)
        createdTo = pytz.utc.localize(current_date).astimezone(
            themarket_tz).replace(tzinfo=None)
        createdFrom = '{:%Y-%m-%dT%H:%M:%S.%fz}'.format(createdFrom)
        createdTo = '{:%Y-%m-%dT%H:%M:%S.%fz}'.format(createdTo)
        return self._load_themarket_order_for_odoo(
            config_app, pageNumber=1, pageSize=499, createdFrom=createdFrom, createdTo=createdTo)
