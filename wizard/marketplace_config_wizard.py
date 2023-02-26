import logging
from odoo.exceptions import UserError
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MarketplaceConfigWizard(models.TransientModel):
    _name = 'marketplace.config.wizard'
    _description = 'Marketplace Config Wizard'

    marketplace_config_ids = fields.Many2many('marketplace.config.details', string='Marketplace Application',  required=True)

    def action_post_data(self):
        ctx = self.env.context
        records = self.env[ctx['active_model']].browse(ctx.get('active_ids', []))
        method = ctx['method']
        config_field = records._fields.get('marketplace_config_ids', 'marketplace_config_id').name
        for config in self.marketplace_config_ids:
            api_provider_name = config.api_provider
            api_provider_obj = self.env['%s' % api_provider_name]
            
            if api_provider_name=="kogan":
                if len(records) > 500:
                    raise UserError(_("Can't push more than 500 Products."))
                else:
                    if hasattr(api_provider_obj, '_post_%s_%s' % (api_provider_name, method)):
                        response = getattr(api_provider_obj, '_post_%s_%s' % (api_provider_name, method))(config, records, config_field)
                        msg = _('Successfully %s(s) Uploaded on %s!' % (method, api_provider_name))
                        if isinstance(response, dict) and not response.get('error_message'):
                            _logger.info('{}'.format(msg))
                        else:
                            _logger.info('{}'.format(msg))
                        

            else:
                if hasattr(api_provider_obj, '_post_%s_%s' % (api_provider_name, method)):
                    for record in records:
                        response = getattr(api_provider_obj, '_post_%s_%s' % (api_provider_name, method))(config, record, config_field)
                        msg = _('Successfully %s(s) Uploaded on %s!' % (method, api_provider_name))
                        if isinstance(response, dict) and not response.get('error_message'):
                            _logger.info('{}'.format(msg))
                        else:
                            _logger.info('{}'.format(msg))
        return {'type': 'ir.actions.act_window_close'}
