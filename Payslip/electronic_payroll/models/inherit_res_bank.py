# -*- coding: utf-8 -*-

from odoo import models, fields

class ResBank(models.Model):
    _inherit = 'res.bank'

    bank_code = fields.Char(string="Bank Code", store=True)
    bank_digi = fields.Char(string="Bank Digital Code", store=True)


class ResPartnerBank(models.Model):  # <- Aquí se corrige la herencia
    _inherit = 'res.partner.bank'

    account_type = fields.Selection([
        ('1', 'Cuenta Corriente'),
        ('2', 'Cuenta de Ahorro'),
    ], string='Account Type', default='1', store=True)
