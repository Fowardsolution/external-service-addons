import io
import base64
from tempfile import TemporaryFile
import pandas
import logging

from odoo import models, api, fields, _
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = "account.move"

    def upload_invoice_from_file(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '',
            'view_mode': 'tree,form',
            'res_model': 'wizard.cardnet.invoice',
            'views': [(self.env.ref(
                'ovillar_features.cardnet_load_file_view').id, 'form')],
            'context': self._context,
            'target': 'new',
        }


class WizardCardnetInvoice(models.TransientModel):
    _name = "wizard.cardnet.invoice"
    _description = "Asistente para cargar facturas CardNet desde Excel"

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Proveedor",
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Diario",
        required=True,
        domain=[('type', '=', 'purchase')],
    )
    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Plazo de pago",
        required=True,
    )
    expense_type = fields.Selection(
        selection=[
            ("01", "01 - Gastos de Personal"),
            ("02", "02 - Gastos por Trabajo, Suministros y Servicios"),
            ("03", "03 - Arrendamientos"),
            ("04", "04 - Gastos de Activos Fijos"),
            ("05", "05 - Gastos de Representación"),
            ("06", "06 - Otras Deducciones Admitidas"),
            ("07", "07 - Gastos Financieros"),
            ("08", "08 - Gastos Extraordinarios"),
            ("09", "09 - Compras y Gastos que forman parte del Costo de Venta"),
            ("10", "10 - Adquisiciones de Activos"),
            ("11", "11 - Gastos de Seguros"),
        ],
        string="Tipo de Costos y Gastos",
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Producto",
        required=True,
        domain=[('type', '=', 'service')],
    )
    cardnet_file = fields.Binary(string="Archivo", )

    def create_invoice_from_file(self):
        move_ids = []
        file = base64.b64decode(self.cardnet_file)
        accounts = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=False)
        tax_id = self.product_id.supplier_taxes_id.filtered(
                        lambda tax: tax.company_id == self.env.user.company_id)

        with io.BytesIO(file) as buffer:
            excel_data_df = pandas.read_excel(
                buffer,
                sheet_name='Hoja1',
                usecols=['Número', 'Fecha', 'Observaciones', 'Monto Comisión']
            )

            for item in excel_data_df.to_dict(orient='record'):
                number = item.get('Número').strip()
                invoice_dict = {
                    'type': 'in_invoice',
                    'partner_id': self.partner_id.id,
                    'journal_id': self.journal_id.id,
                    'invoice_payment_term_id': self.payment_term_id.id,
                    'l10n_do_expense_type': self.expense_type,
                    'user_id': self.env.user.id,
                    'l10n_latam_document_number': number,
                    'invoice_date': item.get('Fecha').strftime("%Y-%m-%d"),
                    'invoice_origin': item.get('Observaciones'),
                    'invoice_line_ids': [(0, 0, {
                        'name': self.product_id.name,
                        'display_type': False,
                        'product_uom_id': 1,
                        'product_id': self.product_id.id,
                        'account_id': accounts['expense'].id,
                        'price_unit': item.get('Monto Comisión'),
                        'quantity': 1,
                        'tax_ids': [(6, 0, tax_id.ids)],
                    })],
                }
                move = self.env['account.move'].sudo().create(
                    invoice_dict).with_user(self.env.uid)
                if not move:
                    raise Warning("Error creando factura: %s" % number)
                move_ids.append(move.id)

        if not move_ids:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': '',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'domain': [('id', 'in', move_ids)],
            'context': self._context,
        }
