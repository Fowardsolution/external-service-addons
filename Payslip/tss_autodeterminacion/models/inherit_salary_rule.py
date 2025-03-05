# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    tss_report = fields.Boolean(string='Para Reporte de TSS')
    tss_columns = fields.Many2many(
        comodel_name='hr.tss_report.tags',
        relation='rule_tag_rel',
        column1='rule_id',
        column2='tag_id',
        string='TSS Columnas',
        help='Indique las columnas donde se introducirá el valor de esta novedad en el reporte de Autodeterminación de la TSS.'
    )

    @api.constrains('tss_report', 'tss_columns')
    def _check_tss_columns(self):
        for rec in self:
            if rec.tss_report and not rec.tss_columns:
                raise ValidationError("Debe indicar las columnas TSS cuando se activa el reporte de TSS.")