# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_draft(self):
        slips = self.slip_ids.filtered(lambda slip: slip.state != 'done')
        slips.action_payslip_draft()
        return super().action_draft()

    def re_calculate(self):
        for slip in self.slip_ids.filtered(lambda s: s.state != 'done'):
            slip.refresh_inputs()
            slip.compute_sheet()

    def verify_payslips(self):
        self.slip_ids.filtered(lambda s: s.state not in ('done', 'cancel')).action_payslip_verify()
        return self.write({'state': 'verify'})

    def remove_slips(self):
        self.slip_ids.filtered(lambda s: s.state not in ('done', 'verify')).unlink()