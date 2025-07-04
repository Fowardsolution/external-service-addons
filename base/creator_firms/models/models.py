# -*- coding: utf-8 -*-

from lxml import etree
from odoo import models, fields, api, _
from odoo.tools.translate import _
import logging
import json
_logger =logging.getLogger(__name__)


class creator_firms(models.Model):
    _name = 'creator_firms.creator_firms'
    _description = 'creator_firms.creator_firms'

    model_ids = fields.Many2one('ir.model')
    view_id = fields.Many2one('ir.ui.view') #domain="[('type', '=', 'qweb')]")
    view_generated = fields.Many2one('ir.ui.view')
    model_data_generated = fields.Many2one('ir.model.data')
    # report_ids = fields.Many2one('ir.actions.report')
    # report_ids = fields.Many2one('ir.ui.view')
    xpath = fields.Char()
    firm_ids = fields.One2many('creator.firms.line', 'creator_id')
    position = fields.Selection(
        selection=[('after', 'After'),
                   ('before', 'Before'),
                   ('inside', 'Inside'), ],required=False, )

    view_type = fields.Selection(
        selection=[
            ('tree', 'Arbol'),
            ('form', 'Formulario'),
            ('qweb', 'QWEB'),
        ],required=False, )
    custom_domain = fields.Char(compute="_compute_model_id")
        # compute="_compute_model_id")

    # @api.depends('model_ids')
    # def _compute_model_id(self):
    #     for rec in self:
    #         index_model = rec.model_ids.model
    #         model = rec.model_ids.model
    #         _logger.error(("MODELO", model))
    #         # self.model_ids.model = str(self.model_ids.model).index(".")
    #         if index_model != False:
    #             index_model = str(index_model).index(".")
    #             model = str(model).lstrip(".")[0:index_model]
            # if rec.model_ids:
            #     rec.custom_domain = [('type', '=', 'qweb')]
            #     _logger.error(("ESTOY DENTRO"))
            #     # rec.custom_domain = [('model_data_id.module', '=', model)]
            #     # rec.custom_domain = ['&',('model_data_id.module', '=', model),('type', '=', 'qweb')]
            #     _logger.error(("ESTOY DENTRO", rec.custom_domain))
            # else:
            #     _logger.error(("ESTOY FUERA"))
            #     rec.custom_domain = [('type', '=', 'qweb')]
    @api.depends('model_ids')
    def _compute_model_id(self):
        for rec in self:
            rec.custom_domain = json.dumps([('type', '=', 'qweb')])
            if rec.model_ids and rec.model_ids.model:
                model_tech = rec.model_ids.model
                try:
                    module = model_tech.split('.')[0]
                except Exception:
                    module = model_tech
                view_data = self.env['ir.model.data'].search([
                    ('module', '=', module),
                    ('model', '=', 'ir.ui.view')
                ])
                view_ids = view_data.mapped('res_id')
                rec.custom_domain = json.dumps([('id', 'in', view_ids)])
                _logger.info("📌 Dominio generado: %s", rec.custom_domain)
        

    def unlink(self):
        if self.view_generated:
            self.view_generated.unlink()

        return super(creator_firms, self).unlink()

    def create_view(self):
        if self.view_generated:
            self.view_generated.unlink()

        firm_list = []
        for rec in self.firm_ids:
            firm_list.append(rec.firms)

        view = self.env['ir.ui.view'].create({
            'name': f'{self.view_ids.name}_inherit',
            'type': self.view_type,
            'model': self.view_ids.model,
            'mode': 'extension',
            'priority': self.view_ids.priority,
            'key': self.view_ids.key,
            'inherit_id': self.view_ids.id,
            'model_data_id': self.view_ids.export_data(['id']),
            'xml_id': self.view_ids.xml_id,
            'arch_base': f'''
        <data inherit_id="{self.view_ids.xml_id}">
        <xpath expr="{self.xpath}" position="{self.position}">
            <div t-attf-class="footer text-center">
              <center>
              <div class="last-page">
               <table class="text-center" style="border:none !important;">
                <tr style="border:none !important;">
                    <span t-foreach="{firm_list}" t-as="i">
                <td style="border:none !important;padding-right:10px;">___________________________________________</td>
                    </span>
                </tr>
                <tr class='text-center' style="border:none !important;">
                    <span t-foreach="{firm_list}" t-as="i"><td style="border:none !important;">
                    <t t-esc="i"/></td>
                    </span>
                    </tr>
                </table>
              </div>
              </center>
              <div style="border-bottom: 2px solid #000; width: 100%;"></div>
              <div t-field="o.company_id.report_footer"/>
              <div t-if="report_type == 'pdf'">
                      Página: <span class="page"/> / <span class="topage"/>
              </div>
              <div t-if="report_type == 'pdf' and display_name_in_footer" class="text-muted">
                      <span t-field="o.name"/>
              </div>
            </div>
          </xpath>
          </data>'''
         })
        self.view_generated = view.id



    def create_model_data(self):
        self.create_view()
        # if self.view_generated:
        #     self.view_generated.unlink()
        if self.model_data_generated:
            self.model_data_generated.unlink()

        if self.view_ids:
            model_data = self.env['ir.model.data'].create({
                    'module': 'creator_firms',
                    'name': f'{self.view_ids.name}_inherit',
                    'display_name': 'test_view_id_model',
                    'model': 'ir.ui.view',
                    'res_id': self.view_generated.id,
                    'reference': 'creator_firms.test_view_id_model',
                })
            self.model_data_generated = model_data.id


class CreatorFirmsLines(models.Model):
    _name = 'creator.firms.line'
    _description = 'Report firm'

    creator_id = fields.Many2one('creator_firms.creator_firms')
    firms = fields.Char(string='Firma:')