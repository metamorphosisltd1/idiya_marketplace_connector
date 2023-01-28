# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    marketplace_config_ids = fields.One2many('marketplace.res.partner', 'partner_id', string="Marketplace Application")
