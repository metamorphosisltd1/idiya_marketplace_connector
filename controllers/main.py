# -*- coding: utf-8 -*-
import base64
from itertools import count
import logging
import json
from math import prod
import random
from time import sleep
import time

import requests
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from ...marketplace_connector.models import themarket_lookup
_logger = logging.getLogger(__name__)


class TradevineExtraImageUpload(http.Controller):
    #------------------------------------------------------------------------#
    # This code uploads and reassigns product template extra medias to
    # Tradevine products
    #------------------------------------------------------------------------#
    @http.route('/marketplace/tradevine/sync-all-products', type='http', auth='user', csrf=False)
    def tradevine_sync_all_product(self, limit=15, offset=0,):
        marketplace_config_ids = request.env['marketplace.config.details'].search([])
        for config in marketplace_config_ids:
            domain = [
                "&",
                "&",
                [
                    "type",
                    "in",
                    [
                        "product"
                    ]
                ],
                [
                    "is_published",
                    "=",
                    True
                ],
                
                [
                    "trade_me_listing_rule_ids",
                    "!=",
                    False
                ],
            ]
            all_product = request.env['product.template'].search(domain)

            len_all_prod = len(all_product)

            _logger.warning(
                "tradevine_sync_all_product  total product found {} ".format(len_all_prod))
            
            offset = int(offset)
            limit = int(limit)
            wiz = request.env['marketplace.config.wizard'].create({
                'marketplace_config_ids':[(4,config.id)]
            })
            
            while (offset < len_all_prod):
                start_time = time.time()
                _logger.warning(
                            "tradevine_sync_all_product limit {}, offset {}".format(limit,offset))
                products = request.env['product.template'].search(domain, limit=limit, offset=offset)
                
                
                wiz.with_context({
                    'active_model': 'product.template',
                    'active_ids': products.ids,
                    'method': 'product'
                }).action_post_data()
                t_time = time.time() - start_time
                if t_time < 60:
                    time.sleep(60 - t_time)                        
                offset += limit
        
       
        return "success"
    
    @http.route('/marketplace/tradevine/outofstockproducts', type='http', auth='public', csrf=False)
    def _get_tradevine_outofstock_products(self):
        outofstocks = []
        tv_products = request.env['product.template'].search([("type","=", "product")]).filtered(lambda p: p.marketplace_config_ids)
        for tv_prod in tv_products:
            for conf in tv_prod.marketplace_config_ids.filtered(lambda conf: conf.config_id.api_provider == 'tradevine'):
                var_stocks = []
                for loc in conf.config_id.location_ids:
                    for variant in tv_prod.product_variant_ids:
                        var_stocks.append(sum(variant.with_context({"location" : loc.id}).mapped("free_qty")))
                if len(var_stocks)>0 and min(var_stocks) == 0:
                    # if tv_prod.bom_ids:
                    #     for bom in tv_prod.bom_ids

                    outofstocks.append(tv_prod.default_code or (tv_prod.x_studio_sku or tv_prod.display_name))
        outofstocks = list(set(outofstocks))
        _logger.warning("Total Out of stock for tradevine is {}".format(len(outofstocks)))
        return "<br/>".join(outofstocks)



    @http.route('/marketplace/tradevine/productimage/upload', type='http', auth='public', csrf=False)
    def _post_tradevine_product_extra_images(self, **post):
        _logger.warning('Beginning _post_tradevine_product_extra_images')
        products = request.env['product.template'].sudo().search([])

        for product in products.filtered(lambda p: p.categ_id.name not in ['Clothing'] or p.categ_id.parent_id.name not in ['Clothing']):
            try:
                _logger.warning(
                    'Beginning _post_tradevine_product_extra_images of product Id : %i' % (product.id))
                if product.product_template_image_ids:
                    _count = 1
                    for img in product.product_template_image_ids:

                        image = {
                            "FileName": product.default_code or product.x_studio_sku + "-"+str(_count)+".jpeg",
                            "ContentsBase64": img.image_1920.decode('utf-8'),
                        }
                        _count += 1
                        listing_rules = product.trade_me_listing_rule_ids
                        for listing_rule in listing_rules.filtered(lambda c: c.config_id.api_provider == "tradevine"):
                            provider_config = listing_rule.config_id
                            _logger.warning(
                                'provider_config Name : %s' % (provider_config.name))

                            resp = request.env['marketplace.connector']._synch_with_marketplace_api(
                                api_provider_config=provider_config,
                                http_method='POST',
                                service_endpoint='v1/Photo',
                                params={},
                                data=json.dumps(image),
                            )
                            if isinstance(resp, dict) and not resp.get('error_message'):
                                _logger.warning(
                                    'PhotoID {}'.format(resp.get('PhotoID'))
                                )
                            time.sleep(1)

            except:
                continue

        return "success"
    
    @http.route('/marketplace/tradevine/pull/sales', type='http', auth='public', csrf=False)
    def _cron_fetch_online_sale_order_tradevine(self, **post):
        _count = 0
        config = request.env['marketplace.config.details'].sudo().search([("id", "=",post.get('config_id'))], limit=1)
        request.env['tradevine'].cron_fetch_online_sale_order_tradevine(config)
        return "success"
    
    @http.route('/marketplace/tradevine/stock/update', type='http', auth='public', csrf=False)
    def _post_tradevine_product_stock_update(self, **post):
        _count = 0

        product_variants = request.env['product.product'].sudo().search([])
        for variant in product_variants.filtered(lambda v: len(v.product_tmpl_id.trade_me_listing_rule_ids)>0 and len(v.marketplace_config_ids)>0):
            variant._call_to_update_marketplace_product_stock()
            _count += 1
            time.sleep(1.5)
        return "total attempted products {}".format(_count)

    @http.route('/marketplace/tradevine/rule/update', type='http', auth='public', csrf=False)
    def _post_tradevine_product_stock_update(self, **post):
        _count = 0
        config = request.env['marketplace.config.details'].sudo().search([("id", "=",post.get('config_id'))], limit=1)
        # api_provider_name = config.api_provider
        # api_provider_obj = request.env['%s' % api_provider_name]
        products = request.env['product.template'].sudo().search([])
        for product in products.filtered(lambda p: len(p.trade_me_listing_rule_ids)>0 ):
            _logger.warning("product :-> {}".format(product.display_name))
            for rule in product.trade_me_listing_rule_ids:
                rule.write({'buy_now_max_qty' : 0.0})
                _logger.warning("rule id {}, max_qty {}".format(rule.id, rule.buy_now_max_qty))

            for variant in product.product_variant_ids:
                variant._call_to_update_marketplace_product_stock()
            self._post_trade_me_listing_rule(config, product)
            _count += 1
            time.sleep(2)
        _logger.warning("total attempted products {}".format(_count))
        return "total attempted products {}".format(_count)

    def _post_trade_me_listing_rule(self, provider_config,  product, resp={}, config_app=False, params=None):
        for rule in product.trade_me_listing_rule_ids.filtered(lambda r: r.ref_code and r.marketplace_product.ref_code):
            data = {
                'TradeMeListingRuleID': rule.ref_code ,
                'ProductID': rule.marketplace_product.ref_code,
                'ProdcutCode': rule.marketplace_product.product_id.default_code or None,
                'RuleName': rule.name,
                'Title': rule.title,
                'SubTitle': rule.subtitle,
                'ExternalTradeMeOrganisationName': rule.external_trade_me_organisation_name,
                'CategoryNumber': rule.category_number.marketplace_catg_ref_number,
                # 'Description':str(rule.description)[:2047] or '',
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
            _logger.warning('_post_trade_me_listing_rule data {}'.format(data))
            resp = self.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=provider_config,
                http_method='POST',
                service_endpoint='v1/TradeMeListingRule/%s' % rule.ref_code,
                params=params or {},
                data=json.dumps(data),
            )

            if isinstance(resp, dict) and not resp.get('error_message'):
                rule.ref_code = resp.get('TradeMeListingRuleID')
            time.sleep(1)










    @http.route("/marketplace/themarket/colormapping", type='http', auth='public', csrf=False)
    def _themarket_color_mapping(self, **post):
        data = {}
        provider_config = request.env['marketplace.config.details'].sudo().search(
            [('api_provider', '=', 'themarket')], limit=1)
        product = request.env["product.template"].sudo().search(
            ['|', ('default_code', '=', post.get("pcode")), ('x_studio_sku', '=', post.get("pcode"))], limit=1)
        if product:
            SkuList = self._prepare_themarket_skus(product)
            ColorImageListMap = self._get_themarket_colorImageListMap(product)


            style = {
                "StyleCode": product.default_code or product.x_studio_sku,
                "PriceRetail":  product.list_price,
                "BrandId": int(product.themarket_brand_id.ref_code),
                "StatusId": 2,
                "SeasonId": 0,
                "BadgeId": 0,
                "GeoCountryId": 0,
                "DisplayRanking": 0,
                "TaxClassId": 1,
                "IsDangerousGoods": int(product.is_fragile),
                "IsBulky": 1 if product.weight > 20 else 0,
                "IsBrandedImport": 1,
                "IsLocal": 0,
                "IsDeliveryDate": 0,
                "IsOverride": 0,
                "IsClickAndCollect": int(product.is_click_and_collect),
                "IsDelivery": int(product.is_click_and_collect),
                "IsSoldSeparately": 1,
                "SkuTypeId": 1,
                "ShippingVolume": float(product.volume),
                "ShippingWeight": float(product.weight),
                "ShippingWidth":  float(product.width)*10,
                "ShippingDepth":  float(product.length)*10,
                "ShippingHeight":  float(product.height)*10,
                "ShippingSizeId": 0,
                "DeliveryTimeId": 0,
                "ConditionId": 1,
                "WebKey": product.name,
                "MaxBuyQty": 2,
                "IsHideSavings": 0,
                "RestrictSalesChannelId": 0,
                "StyleSkuName": product.name,
                "StyleSkuDesc": product.description_sale,
                "CategoryPriorityList": [
                    {
                        "CategoryId": int(product.themarket_category_id.marketplace_catg_ref_number),
                        "Priority": 0
                    }
                ],
                "SkuList": SkuList,
                "ColorImageListMap": ColorImageListMap,
                "DescriptionImageList": []
            }

            data.update(
                {
                    "style": style,
                    "MerchantId": provider_config.themarket_merchantid,
                    "originalStyleCode": product.default_code or product.x_studio_sku
                }
            )
        
        resp = request.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='api/product/style/create', #service_endpoint='api/product/style/update'
            data=json.dumps(data),
        )

        return json.dumps(resp)
    
    
    @http.route("/marketplace/themarket/update/inventory", type='http', auth='public', csrf=False)
    def _get_themarket_product(self, product =False, **post):

        product = product or request.env["product.template"].sudo().search(
            ['|', ('default_code', '=', post.get("pcode")), ('x_studio_sku', '=', post.get("pcode"))], limit=1)

        provider_config = request.env['marketplace.config.details'].sudo().search(
            [('api_provider', '=', 'themarket')], limit=1)

        themarket_rule = product.mapped('themarket_listing_rule_ids').filtered(lambda r: r.config_id.id == provider_config.id)[0]
        

        params = {
            "cc":"EN",
            "merchantid":provider_config.themarket_merchantid,
            "stylecode": product.default_code or product.x_studio_sku
        }
        
        resp = request.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/product/style/view', #service_endpoint='api/product/style/update'
            params=params,
        )
        if isinstance(resp, dict) and not resp.get('error_message'):
            if len(resp.get('SkuList')) >  0:
                self._post_themarket_inventory_update(resp.get('SkuList'))
                # for sku in resp.get('SkuList'):
                #     variant = request.env['product.product'].sudo().search(
                #         ['|', ('default_code', '=',sku.get('SkuCode')), ('x_studio_sku', '=', sku.get('SkuCode'))], limit=1)
                #     if variant:
                #         variant.themarket_sku_ref = sku.get('SkuId')
            themarket_rule.ref_code = resp.get("StyleId")
        return json.dumps(resp)

    def _post_themarket_inventory_update(self, sku_list):
        for sku in sku_list:
            loc_id, invt_id = self._get_themarket_sku_inv(sku)
            self._update_themarket_product_stock(sku,loc_id, invt_id)
        return True


    def _get_themarket_sku_inv(self,sku):
        provider_config = request.env['marketplace.config.details'].sudo().search(
            [('api_provider', '=', 'themarket')], limit=1)

        params = {
            "cc":"EN",
            "merchantid":provider_config.themarket_merchantid,
            "skuid": sku.get('SkuId')
        }
        
        resp = request.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='GET',
            service_endpoint='api/inventory/list/sku',
            params=params,
        )
        _logger.info('inventory List : {}'.format(resp))
        if isinstance(resp, dict) and len(resp.get('InventoryList'))>0 and not resp.get('error_message'):
            inv = resp.get('InventoryList')[0]
            return inv.get('InventoryLocationId'), inv.get('InventoryId') or 0
    
    def _update_themarket_product_stock(self, sku,loc_id, invt_id):
        provider_config = request.env['marketplace.config.details'].sudo().search(
            [('api_provider', '=', 'themarket')], limit=1)
        variant = request.env['product.product'].sudo().search(
                        ['|', ('default_code', '=',sku.get('SkuCode')), ('x_studio_sku', '=', sku.get('SkuCode'))], limit=1)
        data = {
                "InventoryId": invt_id,
                "QtyAssigned": sum(variant.mapped('free_qty')),
                "IsPerpetual": 0,
                "SkuId": sku.get('SkuId'),
                "InventoryLocationId": loc_id,
                "MerchantId": provider_config.themarket_merchantid,
            }
        
        resp = request.env['marketplace.connector']._synch_with_marketplace_api(
            api_provider_config=provider_config,
            http_method='POST',
            service_endpoint='api/inventory/save',
            data=json.dumps(data),
        )
        _logger.info('inventory update : {}'.format(resp))
        return True
            

    def _prepare_themarket_skus(self, product):
        varients = product.mapped("product_variant_ids")

        sku_list = []

        if len(varients) > 1:
            for variant in varients:
                size_label = variant.mapped('product_template_attribute_value_ids').filtered(
                    lambda v: v.attribute_id.name == 'Size')[0].product_attribute_value_id.name

                color_label = variant.mapped('product_template_attribute_value_ids').filtered(
                    lambda v: v.attribute_id.name == 'Color')[0].product_attribute_value_id.name

                color = self._get_themarket_color_id(color_label)

                sku_info = {
                    "StatusId": 2,
                    "SkuCode": variant.default_code,
                    "SizeId": self._get_themarket_size_id(size_label),
                    "ColorId": color.themarket_ref,
                    "QtySafetyThreshold": 0,
                    "PriceRetail": variant.lst_price,
                    "ColorKey": color.themarket_color_code,
                    "SizeLabel": size_label,
                    "SourceCategoryCode": product.themarket_category_id.marketplace_path,
                    "SourceSizeCode": size_label,
                    "SourceBrandCode": product.themarket_brand_id.name,
                    "SkuColor": color.name,
                }
                sku_list.append(sku_info)
        else:
            sku_info = {
                "StatusId": 2,
                "SkuCode": product.default_code or product.x_studio_sku,
                "SizeId": 1,
                "ColorId": 1,
                "QtySafetyThreshold": 0,
                "PriceRetail": product.list_price,
                "ColorKey": "NoColor",
                "SizeLabel": "No Size",
                "SourceCategoryCode": product.themarket_category_id.marketplace_path,
                "SourceSizeCode": "NoSize",
                "SourceBrandCode": product.themarket_brand_id.name,
                "SkuColor": "No Color",
            }
            sku_list.append(sku_info)
        sku_list[0].update({"IsDefault": 1})
        return sku_list

    def _get_themarket_colorImageListMap(self, product):
        color_image_list = {}
        att_line_id = False

        if product.attribute_line_ids:
            for att_line in product.attribute_line_ids.filtered(lambda l: l.attribute_id.name == 'Color'):
                att_line_id = att_line.id
        if att_line_id:
            color_att_vals = request.env['product.template.attribute.value'].sudo().search(
                [('attribute_line_id', '=', att_line_id), ('product_tmpl_id', '=', product.id)])

            for val in color_att_vals:
                variant = val.mapped('ptav_product_variant_ids')[0]
                color = self._get_themarket_color_id(
                    val.product_attribute_value_id.name)
                color_images = []
                _count = 1
                if variant.image_1920 and variant.image_url:
                    image_name = variant.default_code or variant.x_studio_sku + ".jpg"
                    image_key = self._post_themarket_product_image(
                        image_name, variant.image_url)
                    if image_key:
                        color_images.append(
                            {
                                "ColorKey": color.themarket_color_code,
                                "ImageKey":  image_key,
                                "Position": _count
                            }
                        )
                        _count += 1
                if variant.product_variant_image_ids and variant.sh_extra_image_url:
                    for img in variant.sh_extra_image_url.split(","):
                        if _count < 10:
                            image_name = variant.default_code or variant.x_studio_sku + \
                            '-'+str(_count)+".jpg"
                            image_key = self._post_themarket_product_image(
                                image_name, img)
                            if image_key:
                                color_images.append({
                                    "ColorKey": color.themarket_color_code,
                                    "ImageKey": image_key,
                                    "Position": _count
                                })
                                _count += 1

                if len(color_images) > 0:
                    color_images[0].update({"IsDefault": 1, })
                    color_image_list.update({
                        str(color.themarket_color_code): color_images
                    })
        else:
            _count = 1
            color = request.env['themarket.color.mapping'].sudo().browse(2)
            color_images = []
            if product.image_1920 and product.image_url:
                image_name = product.default_code or product.x_studio_sku + ".jpg"
                image_key = self._post_themarket_product_image(
                    image_name, product.image_url)
                if image_key:
                    color_images.append(
                        {
                            "ColorKey": color.themarket_color_code,
                            "ImageKey":  image_key,
                            "Position": _count
                        }
                    )
                    _count += 1
            if product.sh_extra_image_url:
                for img in product.sh_extra_image_url.split(","):
                    if _count < 10:
                        image_name = product.default_code or product.x_studio_sku + \
                        '-'+str(_count)+".jpg"
                        image_key = self._post_themarket_product_image(
                            image_name, img)
                        if image_key:
                            color_images.append({
                                "ColorKey": color.themarket_color_code,
                                "ImageKey": image_key,
                                "Position": _count
                            })
                            _count += 1

            if len(color_images) > 0:
                color_images[0].update({"IsDefault": 1, })
                color_image_list.update({
                    str(color.themarket_color_code): color_images
                })

        return color_image_list

    def _get_themarket_size_id(self, size_label):
        size_list = themarket_lookup.GENERAL_STATUS["SizeList"]
        s = False
        for size in size_list:
            if size['SizeCode'] == size_label and size["StatusId"] == 2:
                s = int(size['SizeId'])
        return s if s else 1

    def _get_themarket_color_id(self, color_label):
        colors = request.env['themarket.color.mapping'].sudo().search([])
        _logger.info("Colors Label: {}".format(color_label))
        c = False
        for color in colors:
            # _logger.info("Color name: {} - {}".format(color.id, color.name))
            # _logger.info("child Colors: {}".format(color.child_colors.split(",") if color.child_colors else ''))
            if color.child_colors and color_label in color.child_colors.split(","):
                c = color
        return c if c else colors[1]

    def _post_themarket_product_image(self, image_name, image):
        _logger.info('TheMaket Uploading photo {}'.format(image_name))
        provider_config = request.env['marketplace.config.details'].sudo().search(
            [('api_provider', '=', 'themarket')], limit=1)
        if "http://" in image or "https://" in image:
            files = [
                ('file', (image_name,requests.get(image, stream=True).raw,'image/jpg'))
                ]
            _logger.info('TheMaket Uploading photo {}'.format(type(image)))
            resp = request.env['marketplace.connector']._synch_with_marketplace_api(
                api_provider_config=provider_config,
                http_method='POST',
                service_endpoint='api/image/upload',
                params={"b": "productimages"},
                files=files,
            )
            # return False
            time.sleep(1)

            if isinstance(resp, dict) and resp.get("ImageKey") and not resp.get('error_message'):
                return resp.get("ImageKey")
            else:
                _logger.error("Error in TheMarket Image Upload {}".format(
                    resp.get('error_message')))
                return False
        else:
            _logger.error("Invalid image link {}".format(
                image))
            return False