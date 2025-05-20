from odoo import models, fields, api
import logging
from lxml import etree

_logger = logging.getLogger(__name__)


class SalesPaymentReport(models.Model):
    _name = 'palo.sale.report'
    _rec_name = 'sale_order_id'
    _description = 'Reporte Pagos y Ventas'

    active = fields.Boolean(default=True, string="Activo")
    sale_order_id = fields.Many2one('sale.order', string='No. Venta')
    payment_id = fields.Many2many('account.payment', string='No. Pago')
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)
    currency_id_signed = fields.Many2one('res.currency', string="Currency Signed", compute="_currency_compute")
    partner_id = fields.Many2one('res.partner', string="Cliente")
    total_sale = fields.Monetary(string="Total Venta")
    total_sale_usd = fields.Monetary(string="Total Venta USD", currency_field='currency_id_signed')
    total_payment = fields.Monetary(string='Total Pago')
    total_payment_usd = fields.Monetary(string='Total Pago USD', currency_field='currency_id_signed')
    difference = fields.Monetary(string='Diferencia Total', compute="_total_difference")
    difference_usd = fields.Monetary(string='Diferencia USD', compute="_total_difference",
                                     currency_field='currency_id_signed')

    @api.depends('total_sale', 'total_payment')
    def _total_difference(self):
        for rec in self:
            rec.difference = rec.total_sale - rec.total_payment
            rec.difference_usd = rec.total_sale_usd - rec.total_payment_usd

    @api.depends('total_sale')
    def _currency_compute(self):
        currency_usd = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        for rec in self:
            if rec.sale_order_id:
                if rec.currency_id != rec.sale_order_id.currency_id:
                    rec.currency_id_signed = rec.sale_order_id.currency_id
                else:
                    rec.currency_id_signed = currency_usd

    # Método para generar el reporte
    @api.model
    def _generate_report(self):
        # Borra registros anteriores
        company_id = self.env.company.id
        company_id2 = self.env.company
        currency_id = self.env.user.company_id.currency_id
        currency_usd = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

        # Consulta para obtener el ID de las órdenes de venta y los pagos asociados
        self.env.cr.execute(f"""
            SELECT so.id as sale_order_id, 
                   ap.id as payment_id,
                   so.currency_id as currency,
                   so.date_order as fecha,
                   ap.currency_id as pay_currency,
                   am.date as fecha_pago,
                   am.state as state_pago,
                   sum(so.amount_total) as amount_total,
                   sum(ap.amount) as pay_total
            FROM sale_order so
            LEFT JOIN account_payment ap ON so.id = ap.sale_id
            LEFT JOIN account_move am ON ap.move_id = am.id
            WHERE so.company_id = {company_id} 
            AND so.state in ('sent', 'sale', 'done')
            GROUP BY so.id, ap.id, am.date, am.state
        """)

        query_results = self.env.cr.dictfetchall()

        existing_reports = {report.sale_order_id.id: report for report in self.with_context(active_test=False).search([])}
        sale_orders = list(existing_reports.keys())

        processed_orders = set()  # Conjunto para llevar un registro de las órdenes de venta ya procesadas
        for result in query_results:
            sale_order = self.env['sale.order'].browse(result['sale_order_id'])
            sale_order_id = result['sale_order_id']
            payment_id = self.env['account.payment'].browse(result['payment_id'])
            payment_ids = [payment['payment_id'] for payment in query_results if
                           payment['sale_order_id'] == sale_order_id and payment['state_pago'] == 'posted']

            account_payments = []
            total_payment = sum(payment['pay_total'] for payment in query_results if
                                payment['sale_order_id'] == sale_order_id and payment['state_pago'] == 'posted' and
                                payment['pay_total'] is not None)
            total_payment_usd = sum(payment['pay_total'] if payment['pay_currency'] != currency_id.id else
                                    currency_id._convert(payment['pay_total'], currency_usd, company_id2,
                                                         payment['fecha_pago'])
                                    for payment in query_results
                                    if
                                    payment['sale_order_id'] == sale_order_id and payment['state_pago'] == 'posted' and
                                    payment['pay_total'] is not None)

            if total_payment and payment_id.currency_id.name != 'DOP':
                total_payment = payment_id.currency_id._convert(total_payment_usd, company_id2.currency_id, company_id2,
                                                                result['fecha_pago'])
            if total_payment_usd is not None:
                total_payment_usd = currency_id._convert(total_payment_usd, currency_id, company_id2, result['fecha'])

            if sale_order_id not in sale_orders:
                account_payments.append(payment_id.id)  # Agregar el ID del pago actual a la lista
                create_lines = self.create({
                    'sale_order_id': sale_order_id,
                    'payment_id': [(6, 0, payment_ids)] if payment_id else None,
                    'partner_id': sale_order.partner_id.id,
                    'total_sale': result[
                        'amount_total'] if sale_order.currency_id == currency_id else sale_order.currency_id._convert(
                        result['amount_total'], currency_id, company_id2, sale_order.date_order),
                    'total_sale_usd': result[
                        'amount_total'] if sale_order.currency_id != currency_id else sale_order.currency_id._convert(
                        result['amount_total'], currency_usd, company_id2, sale_order.date_order),
                    'total_payment': total_payment,
                    'total_payment_usd': total_payment_usd

                })
                sale_orders.append(sale_order_id)

    @api.model
    def read(self, fields=None, load='_classic_read'):
        res = super(SalesPaymentReport, self).read(fields, load)
        self._generate_report()
        return res