# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

from ..generators.interface import GeneratorType

_logger = logging.getLogger(__name__)

class ElectronicPayroll(models.Model):
    _name = 'electronic.payroll'
    _description = 'Electronic Payroll'
    
    name = fields.Char(readonly=True)
    effective_date = fields.Date(string='Effective Date', required=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Run', required=True)
    origin_account = fields.Char(string='Num. Origin Account')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    electronic_payroll_type = fields.Selection(related='company_id.electronic_payroll_type', string='Type')
    binary = fields.Binary(readonly=True)
    binary_name = fields.Char(readonly=True)
    total = fields.Float(compute='_compute_totals', string='Total')
    total_valid = fields.Float(compute='_compute_totals', string='Total to Paid')
    line_ids = fields.One2many('electronic.payroll.line', 'electronic_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validated'),
        ('done', 'Done')
    ], string="Status", default='draft', tracking=True)

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        if self.payslip_run_id:
            self.effective_date = self.payslip_run_id.date_end

    def action_validate(self):
        """ Valida la nómina electrónica y cambia el estado """
        for record in self:
            record.state = 'validate'

    def action_done(self):
        """ Marca la nómina electrónica como finalizada """
        for record in self:
            record.state = 'done'

    def action_draft(self):
        """ Regresa la nómina electrónica a borrador """
        for record in self:
            record.state = 'draft'

    @api.depends('line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.total = sum(line.amount for line in rec.line_ids if line.amount)
            rec.total_valid = sum(line.amount for line in rec.line_ids if not line.no_file and line.amount)

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        if self.payslip_run_id:
            self.effective_date = self.payslip_run_id.date_end

    @api.model_create_multi
    def create(self, vals_list):
        """ Mejorado para procesar múltiples registros de una vez """
        company = self.env.company
        code = company.electronic_payroll_type

        if not code:
            raise UserError("Your Company doesn't have Electronic Payroll configuration")

        for vals in vals_list:
            seq = self.env['ir.sequence'].next_by_code('EP')

            if code == 'BPD':
                date = fields.Date.to_date(vals.get('effective_date'))
                vals['name'] = 'PE{num:>05}{ts}{mm:>02}{dd:>02}{seq}E'.format(
                    num=company.electronic_payroll_bank_code,
                    ts='01', mm=date.month, dd=date.day, seq=seq
                )
            else:
                vals['name'] = f"{code}{seq}"

        return super().create(vals_list)

    def set_line_ids(self):
        """ Crea líneas de pago electrónicas basadas en los empleados de la nómina """
        for electronic in self:
            if electronic.line_ids:
                raise UserError('Lines are already loaded.')

            lines = []
            for slip in electronic.payslip_run_id.slip_ids:
                employee = slip.employee_id
                amount = slip._get_salary_line_total('NET')
                no_file = not amount or not employee.bank_account_id

                lines.append((0, 0, {
                    'employee_id': employee.id,
                    'amount': amount,
                    'no_file': no_file,
                }))

            electronic.write({'line_ids': lines})

    def generate_txt(self):
        """ Genera archivo TXT con la información de la nómina electrónica """
        if not self.line_ids:
            raise UserError('There are no lines to generate the file.')

        ep_type = self.company_id.electronic_payroll_type
        if not ep_type:
            raise UserError("Your Company doesn't have Electronic Payroll configuration")

        records_without_bank = self.line_ids.filtered(lambda r: not r.no_file and not r.bank_account_id)
        if records_without_bank:
            raise UserError('There are employees without Bank Account')

        generator = GeneratorType.get(ep_type)
        file_io, file_value = generator.generate_txt(self)

        self.write({'binary': file_io, 'binary_name': f"{self.name}.txt"})


class ElectronicPayrollLine(models.Model):
    _name = 'electronic.payroll.line'
    _description = 'Electronic Payroll Line'

    electronic_id = fields.Many2one('electronic.payroll', string='Electronic Payroll', ondelete="cascade")
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account', readonly=True, 
                                      related='employee_id.bank_account_id', store=True)
    amount = fields.Float('Amount', readonly=True)
    no_file = fields.Boolean(string='No va al TXT')
