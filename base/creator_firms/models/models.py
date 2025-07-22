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
    view_ids = fields.Many2one('ir.ui.view') #domain="[('type', '=', 'qweb')]")
    view_generated = fields.Many2one('ir.ui.view')
    model_data_generated = fields.Many2one('ir.model.data')
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
                <style type="text/css">
                    .no-borders *, .no-borders td, .no-borders tr, .no-borders table {{
                      border: none !important;
                    }}
                </style>
              <center>
              <div class="last-page">
               <table class="no-borders" style="border: none; border-collapse: collapse; width: 100%;">
                <tr style="border:none !important;">
                    <t t-foreach="{firm_list}" t-as="i">
                        <td style="border:none !important;padding-right:10px;text-align: center;">___________________________________________</td>
                    </t>
                </tr>
                <tr style="border:none !important;">
                    <t t-foreach="{firm_list}" t-as="i">
                        <td style="border:none; text-align: center;">
                            <t t-esc="i"/>
                        </td>
                    </t>
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