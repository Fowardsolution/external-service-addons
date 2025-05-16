from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    product_cost_total = fields.Monetary(
        compute='_compute_product_cost_total', string='Costo productos',)
    margin_total = fields.Monetary(
        compute='_compute_product_cost_total', string='Margen',)
    product_qty = fields.Float(
        compute='_compute_product_cost_total', string='Margen',)

    def _compute_product_cost_total(self):
        for invoice in self:
            if invoice.type != 'out_invoice':
                invoice.product_cost_total = 0.0
                invoice.margin_total = 0.0
                invoice.product_qty = 0.0
            else:
                cost_total = sum([line.product_id.standard_price
                                  for line in invoice.invoice_line_ids])
                product_qty = invoice.invoice_line_ids.mapped('product_id')
                invoice.product_cost_total = cost_total
                invoice.margin_total = invoice.amount_untaxed - cost_total
                invoice.product_qty = len(product_qty)

    def post(self):
        super(AccountMove, self).post()
        for move in self:
            if move.state == 'posted' and move.team_id.use_in_mall_report:
                move._add_invoice_in_mall_report()
        return True

    def create_mall_report_lines(self):
        mall_report = self.env['agora.mall.report'].search([])
        mall_report.unlink()
        team_id = self.env['crm.team'].search([
            ('use_in_mall_report', '=', True)])
        moves = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('type', '=', 'out_invoice'),
            ('team_id', '=', team_id.id),
        ])
        for move in moves:
            if not move.amount_total_signed:
                continue
            move._add_invoice_in_mall_report()
        return True

    def _add_invoice_in_mall_report(self):
        currency = self.env['res.currency'].search([('name', '=', 'USD')])
        sale_order = False
        if self.invoice_origin:
            sale_order = self.env['sale.order'].search([
                ('name', '=', self.invoice_origin)])

        if not sale_order:
            return True

        move_date = self.invoice_date or fields.Date.today()
        str_date = move_date.strftime("%d/%m/%Y")
        hour = int(sale_order.date_order.hour)

        currency_rate_id = self.env['res.currency.rate'].search([
            ('name', '=', move_date),
            ('currency_id', '=', currency.id),
            ('company_id', '=', self.company_id.id)])
        if currency_rate_id:
            currency_rate = 1 / currency_rate_id.rate
        else:
            currency_rate_id = self.env['res.currency'].search([
                ('currency_id', '=', currency.id),
                ('company_id', '=', self.env.company.id),
            ], limit=1, order="name ASC")
            currency_rate = 1 / currency_rate_id.rate

        line = self.env['agora.mall.report'].search([
            ('date', '=', str_date),
            ('hour', '=', hour),
        ])
        product_total = sum(l.quantity for l in self.invoice_line_ids)

        if line:
            line.write({
                'product_total': line.product_total + product_total,
                'sale_per_hour': line.sale_per_hour + 1,
                'currency_rate': currency_rate,
                'base_total': line.base_total + self.amount_untaxed_signed,
                'tax_total': line.tax_total + self.amount_tax_signed,
                'amount_total': line.amount_total + self.amount_total_signed,
            })
        else:
            line.create({
                'client_number': 205,
                'date': str_date,
                'hour': hour,
                'product_total': product_total,
                'sale_per_hour': 1,
                'currency_rate': currency_rate,
                'base_total': self.amount_untaxed_signed,
                'tax_total': self.amount_tax_signed,
                'amount_total': self.amount_total_signed,
            })

        return True


class AgoraMallReport(models.Model):
    _name = 'agora.mall.report'
    _description = 'Agora Mall Sale Report'
    _rec_name = 'date'

    client_number = fields.Integer("NUMSERIE", default=205, )
    date = fields.Char("FECHA")
    hour = fields.Integer("HORA")
    product_total = fields.Float("TOTALARTICULOS")
    sale_per_hour = fields.Float("TOTALTRANSVENTA")
    currency_rate = fields.Float("TASA")
    base_total = fields.Float("TOTALBRUTO")
    tax_total = fields.Float("TOTALIMPUESTOS")
    amount_total = fields.Float("TOTALNETO")