# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def get_product_price_marketplace(self, product, partner=False):
        """ Use to get product price from pricelsit."""
        return self.get_product_price(product, 1.0, partner=partner, uom_id=product.uom_id.id)
