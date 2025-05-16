from odoo import fields, models, api


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    product_standard_price = fields.Float(string='Costo', readonly=True)

    _depends = {'product.product': ['standard_price'],}

    def _select(self):
        extra_select = ", product.standard_price AS product_standard_price"
        return super()._select() + extra_select

    def _group_by(self):
        return super()._group_by() + ", product.standard_price"