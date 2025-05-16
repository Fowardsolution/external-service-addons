from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_id = fields.Many2one(
        comodel_name='sale.order',
        string='Pedido de venta',
    )
