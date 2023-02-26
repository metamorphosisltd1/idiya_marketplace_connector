# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests


from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20


class MarketPlaceConnector(models.AbstractModel):
    _name = 'marketplace.connector'
    _description = 'MarketPlace API connector'

    def _get_api_end_point_url(self, marketplace):
        return marketplace.sudo().api_url

    def _synch_with_marketplace_api(self, api_provider_config, http_method, service_endpoint, public_service_endpoint=False, params=None, data=None, files=None):

        params = params or {}
        data = data or {}
        files = files or {}
        headers = {}

        api_url = self._get_api_end_point_url(api_provider_config)
        if public_service_endpoint:
            service_url = service_endpoint
        else:
            service_url = '{}/{}'.format(api_url, service_endpoint)

            func = '{}:{}'.format(http_method, service_endpoint)

            api_provider = api_provider_config.api_provider
            api_provider_obj = self.env['%s' % api_provider]

            if hasattr(api_provider_obj, '_get_%s_oauth_header' % api_provider):
                headers = getattr(api_provider_obj, '_get_%s_oauth_header' % api_provider)(api_provider_config)
            if len(files) > 0:
                headers.pop('Content-Type')
            # elif len(data)> 0 and  json.loads(data):
            #     headers['Content-Type'] = "application/json"

        response = {}
        try:
            _logger.warning('sent data for {}:{} \n params: {}\n data: {}\n with header:{} '.format(http_method,service_url, params,data,headers))
            resp = requests.request(
                http_method, service_url,
                headers=headers,
                params=params,
                data=data,
                files=files,
                timeout=TIMEOUT)
            _logger.warning('request url : {}'.format(resp.url))
            # _logger.warning('response from marketplace post/get (HTTP status {})'.format(resp.content))
            resp.raise_for_status()
            if resp.text != 'null' and bool(resp.text):
                if isinstance(resp.content, str):
                    response = resp.json()
                else: 
                    response = resp.content
            else:
                response = resp.text

        except requests.HTTPError:
            level = 'warning'
            if resp.text:
                try:
                    response = json.loads(resp.text)
                    if isinstance(response, list):
                        response = response[0]
                    message = response.get('message') or response.get('error') or "{} : {}".format(response.get('AppCode'), response.get('Message'))
                except:
                    message = resp.text
            else:
                message = _('Unexpected error ! please report this to your administrator.')
            _logger.error('{}'.format(message))
            response['error_message'] = message
        except Exception as ex:
            message = _('Unexpected error ! please report this to your administrator.')
            _logger.error('{}'.format(ex))
            response['error_message'] = _('Unexpected error ! please report this to your administrator.')

        # Convert received response to dictionary
        if response and not isinstance(response, dict):
            response = json.loads(response)

        # if 'error_message' in response and not self.env.uid == 1 :
        #     raise UserError(response['error_message'])
        
        return response
