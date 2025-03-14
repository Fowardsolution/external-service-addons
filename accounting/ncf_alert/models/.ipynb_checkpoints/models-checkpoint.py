# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger =logging.getLogger(__name__)

class l10n_do_sequence_inherit(models.Model):
    _name = 'l10n.sequence.max'
    
    document_type_id = fields.Many2one("l10n_latam.document.type")
    company_id = fields.Many2one("res.company")
    max = fields.Integer()
    max_alert = fields.Integer()
    user_id = fields.Many2one('res.users')
    
    def action_send_email(self):
        mail_template = self.env.ref('l10n_do_sequence_inherit.email_template')
        mail_template.send_mail(self.id, force_send=True)

    
class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        l10n_max = self.env['l10n.sequence.max'].search([
            ('company_id', '=', self.company_id.id),
            ('document_type_id', '=', self.l10n_latam_document_type_id.id),
        ])
        if 'l10n_do_fiscal_number' in vals and vals['l10n_do_fiscal_number'] != '':
            if int(vals['l10n_do_fiscal_number'][3::]) > l10n_max.max:
                raise UserError(_("El numero maximo de comprobantes a sido excedido" " Favor revisar su numero maximo."))

            if int(vals['l10n_do_fiscal_number'][3::]) >= l10n_max.max_alert:
                l10n_max.action_send_email()
                
        return super(AccountMove,self).write(vals)


