from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Sale(models.Model):
    _inherit = 'sale.order'

    payment_count = fields.Integer(
        string='Pagos',
        compute='_compute_payment_ids',
    )

    @api.depends('name')
    def _compute_payment_ids(self):
        for order in self:
            payments = self.env['account.payment'].search_count([
                ('sale_id', '=', order.id),
                ('state', 'not in', ['draft', 'cancel'])
            ])
            order.payment_count = payments

    def action_view_payments(self):
        return {
            'name': _('Pagos'),
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('sale_id', '=', self.id),
                ('payment_type', '=', 'inbound'),
            ],
            'res_model': 'account.payment',
            'view_id': False,
            'context': {
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_total,
                'default_sale_id': self.id,
                'default_communication': "Pago de %s" % self.name,
                'search_default_inbound_filter': 1,
                'res_partner_search_mode': 'customer',
            },
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(
            self._context.get('active_ids', []))

        for order in sale_orders:
            for line in order.order_line.filtered(
                    lambda line: line.product_id.type == 'product'):
                if line.qty_delivered != line.product_uom_qty:
                    raise ValidationError("No a despachado todos los productos")

        return super(SaleAdvancePaymentInv, self).create_invoices()


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    use_in_mall_report = fields.Boolean("Usar en reporte del Mall")
