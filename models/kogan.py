import logging
import random
import json
import time
import dateutil.parser
from odoo import fields, models, _
from odoo.osv import expression
from ...marketplace_connector.models import kogan_lookup

_logger = logging.getLogger(__name__)


class Kogan(models.AbstractModel):
    _name = 'kogan'
    _description = 'Kogan API'
    
    
    
#GET PRODUCT >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _get_kogan_product_by_id(self, provider_config, product_id, **kwargs):
        '''This method gets an individual product specified by the supplied ID - 
            the output consists of top level product information, including summary inventory quantities
        '''
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='/products/%s' % product_id,
            params={},
            data={},
        )

    def _get_kogan_product_by_paged_list(self, provider_config, pageNumber=1, pageSize=499, **kwargs):
        ''' This method gets a paged list of top level product information, including summary inventory quantities. '''
        params = {
            'pageNumber': pageNumber,
            'pageSize': pageSize,
            **kwargs
        }
        return self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='products',
            params=params,
            data={},
        )

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
            service_endpoint='products',
            params=params,
            data={},
        )

    def _get_kogan_product(self, provider_config, product_id=None, **kwargs):
        if product_id:
            return self._get_kogan_product_by_id(provider_config, product_id, **kwargs)
        if not product_id:
            return self._get_kogan_product_by_paged_list(provider_config, **kwargs)



#GET PRODUCT Value >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>)))))))) 
    def _prepare_product_values(self, product_values, config):
        currency = self.env['res.currency']
        marketplace_brand = self.env['marketplace.product.brand']
        if product_values.get('Currency'):
            currency_name = kogan_lookup.get_currency(
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
    







# Category for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _import_category_from_kogan(self, config, datas, level=0):
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
            
            
    def _load_kogan_category_for_odoo(self, provider_config):
        resp = self.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='category/',
            params={},
            data={},
            public_service_endpoint=True
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            self._import_category_from_kogan(provider_config, resp)
        return resp
    
    
    
    
    
    
    
    
    
# Product for Odoo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _load_kogan_product_for_odoo(self, provider_config, pageNumber=1, pageSize=50):
        response = self._get_kogan_product_by_paged_list(
            provider_config, pageNumber, pageSize) or {}
        total_product = response.get('CountTotal')
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
                    response = self._get_kogan_product_by_paged_list(
                        provider_config, pageNumber, pageSize) or {}
            else:
                break
        return response
    
    
    
    
    
    
    
    
    
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
            service_endpoint='/orders',
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
                    response = self._get_kogan_order_by_paged_list(
                        provider_config, pageNumber, pageSize, createdFrom=createdFrom, createdTo=createdTo) or {}
            else:
                break
        return response
    



# Photo >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _prepare_product_photo_post_data(self, provider_config, product, photoID=None):
        _logger.warning('Kogan product {}, {}, PhotoID {}'.format(product._name, product.id, photoID))
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