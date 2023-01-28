# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from logging import warning


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    marketplace_config_ids = fields.One2many('marketplace.stock.warehouse', 'warehouse_id', string="Marketplace Application", copy=False)


class MarketplaceStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.depends('inventory_quantity')
    def _update_marketplace_product_stock(self):
        warning("_update_marketplace_product_stock for PRoduct Ids {}".format(self.ids))
        for quant in self:
            quant.product_id._call_to_update_marketplace_product_stock()