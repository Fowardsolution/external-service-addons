from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class PayslipInputImport(models.Model):
    _name = "payslip.input.import"
    _description = 'Import Payslip Input'

    name = fields.Char()
    active = fields.Boolean(default=True)
    input_id = fields.Many2one('hr.payslip.input.type', string='Novedad')
    code = fields.Char(related='input_id.code', string='Codigo')
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
    amount = fields.Float(string="Importe")
    frecuency_type = fields.Selection([
        ('fijo', 'Fijo'),
        ('variable', 'Variable')
    ], string="Tipo de frecuencia", default='fijo')
    
    apply_on = fields.Selection([
        ('1', 'Primera Quincena'),
        ('2', 'Segunda Quincena'),
        ('3', 'Primera y Segunda Quincena')
    ], string="Aplicar en", default='1')
    
    frecuency_number = fields.Integer(string="Numero de veces", default=1)
    start_date = fields.Date(string="Fecha inicial")
    end_date = fields.Date(string="Fecha final")
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.company)
    to_force = fields.Boolean('Solo Nómina Especiales')
    notes = fields.Text('Descripción/Notas')

    @api.constrains('frecuency_type', 'start_date', 'frecuency_number')
    def _check_frecuency_requirements(self):
        """ Valida que los campos requeridos estén completos antes de guardar """
        for record in self:
            # Si la frecuencia es variable, los campos deben estar llenos
            if record.frecuency_type == 'variable':
                if not record.start_date:
                    raise ValidationError(_("Debe ingresar una fecha de inicio cuando la frecuencia es 'Variable'."))
                if not record.frecuency_number or record.frecuency_number <= 0:
                    raise ValidationError(_("Debe ingresar un número de frecuencia válido cuando la frecuencia es 'Variable'."))

    @api.depends('input_id', 'code')
    def name_get(self):
        return [(rec.id, f'[{rec.code or ""}] {rec.input_id.name or ""}') for rec in self]
    
    @api.onchange('frecuency_number', 'start_date', 'apply_on')
    def _calc_date_end(self):
        for rec in self:
            if rec.start_date and rec.frecuency_number > 0:
                num_veces = max(0, rec.frecuency_number - 1)
                if rec.apply_on in ('1', '2'):
                    rec.end_date = rec.start_date + relativedelta(months=num_veces)
                elif rec.apply_on == '3':
                    rec.end_date = rec.start_date + relativedelta(months=num_veces // 2, days=15)

