# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    electronic_payroll_type = fields.Selection([
        ('BHD', 'Banco BHD'),
        ('BPD', 'Banco Popular'),
        ('BDR', 'Banco Reservas')
    ], string='Electronic Payroll', store=True)

    electronic_payroll_email = fields.Char(string='Email Payroll', store=True)
    electronic_payroll_bank_code = fields.Char(string='Bank Code', store=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    electronic_payroll_type = fields.Selection(
        related='company_id.electronic_payroll_type',
        readonly=False,
        store=True
    )

    electronic_payroll_email = fields.Char(
        related='company_id.electronic_payroll_email',
        readonly=False,
        store=True
    )

    electronic_payroll_bank_code = fields.Char(
        related='company_id.electronic_payroll_bank_code',
        readonly=False,
        store=True
    )

    module_electronic_payroll_account = fields.Boolean(
        string="Electronic Payroll - Account"
    )

    module_electronic_payroll_batch = fields.Boolean(
        string="Electronic Payroll - Batch Payment"
    )
    
    @api.depends('electronic_payroll_type')
    def _compute_visibility_fields(self):
        for rec in self:
            rec.show_bpd_fields = rec.electronic_payroll_type == 'BPD'

    show_bpd_fields = fields.Boolean(compute="_compute_visibility_fields")

