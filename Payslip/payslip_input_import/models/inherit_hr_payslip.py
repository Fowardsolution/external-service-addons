# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    apply_on = fields.Selection([
        ('1', 'Primera Quincena'),
        ('2', 'Segunda Quincena')
    ], string="Aplicar en", default='1')

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from:
            if self.date_from.day <= 15:
                self.apply_on = '1'  # Primera Quincena
            else:
                self.apply_on = '2'  # Segunda Quincena
    
    @api.model
    def create(self, vals):
        if vals.get('date_from'):
            date_from = fields.Date.to_date(vals['date_from'])
            vals['apply_on'] = '1' if date_from.day <= 15 else '2'
        return super().create(vals)


    def refresh_inputs(self):
        for slip in self.filtered(lambda s: s.state != 'done'):
            _logger.info(f"🔄 Refrescando novedades para: {slip.employee_id.name}")
    
            # Eliminar líneas de entrada previas
            slip.input_line_ids.unlink()
    
            # Obtener novedades
            inputs = slip._get_inputs()
            _logger.info(f"📊 Datos obtenidos de _get_inputs(): {inputs}")
    
            input_lines = []
            
            for input_code, amount in inputs.items():
                input_type = self.env['hr.payslip.input.type'].search([('code', '=', input_code)], limit=1)
                if input_type:
                    _logger.info(f"✔ Agregando novedad {input_code} ({input_type.id}): {amount}")
                    input_lines.append((0, 0, {
                        'payslip_id': slip.id,
                        'input_type_id': input_type.id,
                        'amount': amount
                    }))
            
            if input_lines:
                slip.input_line_ids = input_lines
                _logger.info(f"✅ Se agregaron {len(input_lines)} novedades a la nómina.")
    
            else:
                _logger.info(f"⚠ No se encontraron novedades para {slip.employee_id.name}.")


    def _get_inputs(self):
        """ Recupera las novedades de 'payslip.input.import' y las convierte en inputs de nómina. """
        self.ensure_one()
        apply_on = self.apply_on or ('1' if self.date_from.day <= 15 else '2')
        date_from, date_to = self.date_from, self.date_to
        forced = self._context.get('forced', 0)
    
        _logger.info(f"🔍 Buscando novedades para: {self.employee_id.name}, Fecha desde: {date_from}, hasta: {date_to}")
    
        novedades = self.env['payslip.input.import'].search([
            ('employee_id', '=', self.employee_id.id),
            ('active', '=', True),
            ('company_id', '=', self.contract_id.company_id.id),
            ('to_force', '=', forced),
            '|', ('end_date', '>=', date_from), ('end_date', '=', False)
        ])
    
        _logger.info(f"📌 Novedades encontradas: {len(novedades)}")
    
        data = {}
        for record in novedades:
            if ((not record.end_date or date_from <= record.end_date) and
                (not record.start_date or record.start_date <= date_to) and
                (record.apply_on == apply_on or record.apply_on == '3')):
    
                if record.input_id:
                    code = record.input_id.code
                    data[code] = data.get(code, 0) + record.amount
                    _logger.info(f"✔ Agregando novedad {code}: {record.amount}")
    
        _logger.info(f"📊 Datos de entrada generados: {data}")
        return data



    @api.depends('state')
    def _compute_apply_on(self):
        """ Oculta el campo 'apply_on' si no está en estado 'draft' """
        for record in self:
            record.apply_on = '' if record.state != 'draft' else 'Activo'

    @api.onchange('state')
    def _onchange_state(self):
        """ Muestra un mensaje si el estado cambia y bloquea el botón en ciertos casos """
        if self.state != 'draft':
            return {
                'warning': {
                    'title': "Aviso",
                    'message': "No puedes modificar este campo fuera del estado borrador."
                }
            }

    def action_payslip_verify(self):
        return self.write({'state': 'verify'})



