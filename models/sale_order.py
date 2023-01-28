# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    marketplace_config_id = fields.Many2one('marketplace.order', string="Marketplace Application")
    inventory_adjustment_note = fields.Text()

    def action_post_sale_order_data_on_marketpalce(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.config.wizard',
            'view_mode': 'from',
            'views': [[self.env.ref('marketplace_connector.view_marketplace_config_wizard_form').id, 'form']],
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_ids': self.ids,
                'method': 'sale_order'
            },
            'name': _('Create/Update Sale order for Marketplace Account'),
        }

    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        self.order_line.mapped('product_id')._call_to_update_marketplace_product_stock(sale_order=self)
        return result

    def action_cancel(self):
        result = super(SaleOrder, self).action_cancel()
        self.order_line.mapped('product_id')._call_to_update_marketplace_product_stock(sale_order=self)
        return result

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    marketplace_config_id = fields.Many2one('marketplace.order.line', string="Marketplace Application")
