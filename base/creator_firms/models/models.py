# -*- coding: utf-8 -*-

from lxml import etree
from odoo import models, fields, api, _
from odoo.tools.translate import _
import logging
_logger =logging.getLogger(__name__)


class creator_firms(models.Model):
    _name = 'creator_firms.creator_firms'
    _description = 'creator_firms.creator_firms'

    model_ids = fields.Many2one('ir.model')
    view_ids = fields.Many2one('ir.ui.view') #domain="[('type', '=', 'qweb')]")
    view_generated = fields.Many2one('ir.ui.view')
    model_data_generated = fields.Many2one('ir.model.data')
    report_ids = fields.Many2one('ir.actions.report')
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


    @api.onchange('report_ids')
    def _campus_onchange(self):
        index_model = self.model_ids.model
        model = self.model_ids.model
        # self.model_ids.model = str(self.model_ids.model).index(".")
        if index_model != False:
            index_model = str(index_model).index(".")
            model = str(model).lstrip(".")[0:index_model]
        res = {}

        res['domain'] = {'view_ids': ['&',('model_data_id.module', '=', model),('type', '=', 'qweb')]}
        return res
    @api.onchange('model_ids')
    def _campus_onchange02(self):
        res = {}

        res['domain'] = {'report_ids': [('model', '=', self.model_ids.model)]}
        return res

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