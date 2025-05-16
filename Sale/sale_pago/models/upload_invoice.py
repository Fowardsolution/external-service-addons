import io
import base64
import pandas
import logging
import threading
import sys

from odoo import models, api, fields, _
from odoo.tests.common import Form
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)


class UploadInvoice(models.Model):
    _name = "upload.invoice"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Asistente para cargar facturas desde Excel"

    name = fields.Char(
        string="Nombre",
        store=True,
        copy=False,
        default=lambda self: _('New'),
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Proveedor",
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Diario de factura",
        required=True,
        domain=[('type', '=', 'purchase')],
    )
    bank_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Medio de Pago",
        required=True,
        domain=[('type', '=', 'bank')],
    )
    bank_id = fields.Many2one(
        comodel_name='account.journal',
        string="Banco",
        required=True,
        domain=[('type', '=', 'bank')],
    )
    entry_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Diario para apunte",
        required=True,
        domain=[('type', '=', 'general')],
    )
    # payment_account_id = fields.Many2one(
    #     comodel_name='account.account',
    #     string="Cuenta retención ITBIS",
    #     required=True,
    # )
    itbis_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Cuenta retención ITBIS",
        required=True,
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
    invoice_count = fields.Integer(
        string='Cantidad',
        readonly=True,
        compute="_compute_invoice_count"
    )
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string='Facturas',
        readonly=True,
        copy=False,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'upload.invoice') or _('New')
        record = super(UploadInvoice, self).create(vals)

        return record

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, record.name))
        return res

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id and self.partner_id.l10n_do_expense_type:
            self.expense_type = self.partner_id.l10n_do_expense_type

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            if record.invoice_ids:
                record.invoice_count = len(record.invoice_ids)
            else:
                record.invoice_count = 0

    def create_invoice_from_file(self):
        accounts = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=False)
        tax_id = self.product_id.supplier_taxes_id.filtered(
                        lambda tax: tax.company_id == self.env.user.company_id)
        attachment = self.env['ir.attachment'].search([
            ('res_id', '=', self.id)])
        moves = self.env['account.move']
        with io.BytesIO(base64.b64decode(attachment.datas)) as buffer:
            excel_data_df = pandas.read_excel(buffer, engine='xlrd')

            for item in excel_data_df.to_dict(orient='record'):

                number = item.get('Número*').strip()
                bank_amount = item.get('Monto*')
                itbis_amount = item.get('Monto Retención Impuesto')
                price_unit = item.get('Monto Comisión')
                entry_date = item.get('Fecha*').strftime('%Y-%m-%d')
                credit_amount = bank_amount + itbis_amount + price_unit

                invoice_form = Form(self.env['account.move'].with_context(
                    default_type='in_invoice'))
                invoice_form.partner_id = self.partner_id
                invoice_form.journal_id = self.journal_id
                invoice_form.invoice_payment_term_id = self.payment_term_id
                invoice_form.l10n_do_expense_type = self.expense_type
                invoice_form.l10n_latam_document_number = number
                invoice_form.invoice_date = entry_date

                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.product_id = self.product_id
                    invoice_line_form.name = self.product_id.name
                    invoice_line_form.display_type = False
                    invoice_line_form.account_id = accounts['expense']
                    invoice_line_form.product_uom_id = self.product_id.uom_id
                    invoice_line_form.quantity = 1
                    invoice_line_form.price_unit = price_unit

                    if tax_id:
                        invoice_line_form.tax_ids.add(tax_id)

                move_id = invoice_form.save()
                move_id.post()
                moves |= move_id

                # Jornal entries
                bank_acc_id = self.bank_journal_id.default_debit_account_id.id
                acc_payable_id = self.partner_id.property_account_payable_id.id
                credit_acc_id = self.bank_id.default_credit_account_id.id

                move_entry = self.env['account.move'].create({
                    'type': 'entry',
                    'date': entry_date,
                    'journal_id': self.entry_journal_id.id,
                    'line_ids': [
                        (0, None, {
                            'name': "Medio de pago",
                            'account_id': bank_acc_id,
                            'debit': bank_amount,
                            'credit': 0,
                        }),
                        (0, None, {
                            'name': "ITBIS",
                            'account_id': self.itbis_account_id.id,
                            'debit': itbis_amount,
                            'credit': 0,
                        }),
                        (0, None, {
                            'name': "Cliente",
                            'account_id': acc_payable_id,
                            'partner_id': self.partner_id.id,
                            'debit': price_unit,
                            'credit': 0,
                        }),
                        (0, None, {
                            'name': "/",
                            'account_id': credit_acc_id,
                            'debit': 0,
                            'credit': credit_amount,
                        }),
                    ],
                })
                move_entry.post()

                debit_line_acc_id = self.env['account.move.line'].search([
                    ('move_id', '=', move_entry.id),
                    ('partner_id', '=', self.partner_id.id),
                ])
                move_id.js_assign_outstanding_line(debit_line_acc_id.id)
                _logger.info('Factura creada desde: %s, records %s.' % (
                    self._name, str(number)))

            if moves:
                self.write({
                    'invoice_ids': [(6, 0, moves.ids)],
                    'invoice_count': len(moves)
                })

    def create_invoices(self):
        threaded_calculation = threading.Thread(
            target=self.create_invoice_from_file, args=())
        threaded_calculation.start()
        self.refresh()
        return self.action_view_invoice()

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view)
                                               for state, view in action[
                                                   'views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_type': 'in_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_user_id': self.env.user.id,
            })
        action['context'] = context
        return action
