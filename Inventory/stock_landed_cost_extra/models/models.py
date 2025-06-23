# -*- coding: utf-8 -*-

import logging
from collections import defaultdict, Counter

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.misc import groupby
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    @api.depends('product_list_ids.arancel')
    def _compute_arancel_total(self):
        for record in self:
            record.arancel_total = sum(line.arancel for line in record.product_list_ids)

    def _compute_picking_count(self):
        picking_obj = self.env['stock.picking']
        for rec in self:
            rec.picking_count = picking_obj.search_count(
                [('origin', '=', rec.name)])

    no_cost_lines = fields.One2many(
        'stock.landed.cost.lines.remove', 'cost_id')
    product_list_ids = fields.One2many(
        'stock.landed.cost.product.list', 'cost_id')
    cost_summary_ids = fields.One2many('stock.landed.cost.summary', 'cost_id')
    location_id = fields.Many2one(
        'stock.location', string='Ubicacion de Destino')
    picking_count = fields.Integer(compute="_compute_picking_count")
    arancel_total = fields.Float("Arancel Total", compute="_compute_arancel_total", store=True)

    manifest = fields.Char(string='Manifiesto', required=False)

    purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        string='Ordenes de Compras', domain="[('state', 'in', ('purchase', 'done'))]")

    purchase_info_line_ids = fields.One2many(
        comodel_name='purchase.information.line',
        inverse_name='cost_id',
        string='Purchase Order Information',
        required=False)

    vendor_bill_ids = fields.Many2many(
        comodel_name='account.move',
        string='Facturas',
        domain="[('state', 'not in', ('draft', 'cancel')), ('cost_id', '=', False), ('move_type', '=', 'in_invoice')]"
    )

    vendor_invoice_line = fields.One2many(
        comodel_name='account.move',
        inverse_name='cost_id',
        string='Vendor Invoice Line',
        required=False)

    ref = fields.Char(string='Ref.')
    contenedor = fields.Char(string='Contenedor')
    naviera = fields.Many2one(
        'res.partner',
        string="Naviera"
    )

    mrp_production_ids = fields.Many2many(
        'mrp.production', 
        string='Manufacturing Orders',
        domain="[('state', 'in', ('progress', 'done'))]"
    )

    @api.onchange('purchase_ids')
    def _onchange_purchase_ids(self):
        for purchase in self.purchase_ids:

            for picking in purchase.picking_ids:
                self.picking_ids = [(4, picking.id)]

            for invoice in purchase.invoice_ids:
                self.vendor_bill_ids = [(4, invoice.id)]

    def load_purchases(self):

        if self.purchase_ids:
            self.purchase_info_line_ids.unlink()  # = [(5 ,0 ,0)]

        for purchase in self.purchase_ids:

            for picking in purchase.picking_ids:

                self.env['purchase.information.line'].create({
                    'cost_id': self.id,
                    'picking_id': picking.id,
                    'purchase_id': picking.purchase_id.id,
                    'partner_id': picking.purchase_id.partner_id.id,
                })

            purchase.cost_id = self.id

    def delete_invoice_line_of_stock_landed_cost_lines(self, cost_id, invoice_id):
        self.env['stock.landed.cost.lines'].search([
            ('cost_id', '=', cost_id),
            ('account_move_id', '=', invoice_id),
        ]).unlink()

    def load_invoices(self):
        CostLines = self.env['stock.landed.cost.lines']

        for invoice in self.vendor_bill_ids:
            lines = invoice.invoice_line_ids.filtered(
                lambda r: r.is_landed_costs_line)

            self.delete_invoice_line_of_stock_landed_cost_lines(
                self.id,
                invoice.id
            )

            for line in lines:
                CostLines.create({
                    'cost_id': self.id,
                    'account_id': line.account_id.id,
                    'product_id': line.product_id.id,
                    'account_move_id': invoice.id,
                    'price_unit': invoice.currency_id._convert(
                        line.price_unit,
                        invoice.company_currency_id,
                        invoice.company_id,
                        invoice.invoice_date
                    ),
                    'split_method': line.product_id.split_method_landed_cost or 'equal',
                    'name': line.name
                })

            invoice.cost_id = self.id

    def move_product_to_location(self):
        if not self.location_id:
            raise UserError('Debe de especificar la Ubicacion de Destino.')

        for picking in self.picking_ids:
            int_type = picking.picking_type_id.warehouse_id.int_type_id.id

            new_picking = picking.copy({
                'partner_id': False,
                'picking_type_id': int_type,
                'location_id': picking.location_dest_id.id,
                'location_dest_id': self.location_id.id,
                'origin': self.name,
                'group_id': False,
            })

            # Set quantities automatically and validate the pickings.
            # copied from module sale_workflow
            new_picking.action_assign()
            for move in new_picking.move_ids_without_package.filtered(
                    lambda m: m.state not in ["done", "cancel"]
            ):
            
                rounding = move.product_id.uom_id.rounding
                if (
                    float_compare(
                        move.quantity_done,
                        move.product_qty,
                        precision_rounding=rounding,
                    )
                    == -1
                ):
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
            new_picking.with_context(skip_immediate=True).button_validate()
        return True

    def get_product(self):
        if not self.picking_ids:
            raise UserError(_('You must select at least one transfer.'))

        self.product_list_ids.unlink()

        listado = []
        products = []
        for pick in self.picking_ids:
            for line in pick.move_ids_without_package.filtered(lambda l: l.state == 'done'):
                products.append((0, 0, {
                    'move_id': line.id,
                    'product_id': line.product_id.id,
                    'cost_id': self.id,
                    'name': line.product_id.name,
                }))

        self.product_list_ids = products

    def remove_arancel(self):
        arancel = self.cost_lines.filtered(lambda l: l.arancel_product_id)
        arancel.unlink()

    def set_aranceles(self):
        product = self.env['product.product'].search(
            [('default_code', '=', 'arancel')])
        if not product:
            raise UserError(
                _('You do not have an additional cost configured with an internal reference "arancel".'))

        self.remove_arancel()

        account_id = product.property_account_expense_id or product.categ_id.property_account_expense_categ_id
        aranceles = []
        for product_list in self.product_list_ids:
            if product_list.arancel:
                aranceles.append(
                    (0, 0, {
                        'move_id': product_list.move_id.id,
                        'product_id': product.id,
                        'account_id': account_id.id,
                        'price_unit': product_list.arancel,
                        'arancel_product_id': product_list.product_id.id,
                        'split_method': 'arancel',
                        'name': 'Arancel: %s' % product_list.product_id.display_name
                    })
                )

        if aranceles:
            self.cost_lines = aranceles

    def action_open_pickings(self):
        action = {
            "name": "Trans. Interntas",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["origin", "=", self.name]],
        }
        return action

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        NoCost = self.env['stock.landed.cost.lines.remove']

        cost_totals_type = {}
        digits = self.env['decimal.precision'].precision_get('Product Price')
        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost.picking_ids):

            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    # para prevenir que otros productos tengan el arancel que no le corresponde en cero (0)
                    if cost_line.split_method == 'arancel':
                        if cost_line.move_id.id != val_line_values.get('move_id'):
                            continue

                    totals = {
                        'total_qty': 0.0,
                        'total_cost': 0.0,
                        'total_weight': 0.0,
                        'total_volume': 0.0,
                        'total_line': 0.0,
                    }

                    no_cost = NoCost.search([
                        ('cost_line_id', '=', cost_line.id),
                        ('product_list_id.product_id', '=',
                         val_line_values.get('product_id'))
                    ])

                    if no_cost:
                        continue

                    totals.update({
                        'total_qty': val_line_values.get('quantity', 0.0),
                        'total_cost': val_line_values.get('former_cost', 0.0),
                        'total_weight': val_line_values.get('weight', 0.0),
                        'total_volume': val_line_values.get('volume', 0.0),
                        'total_line': 1,
                    })

                    temp = Counter(totals)
                    if cost_line.id not in cost_totals_type:
                        cost_totals_type[cost_line.id] = temp

                    else:
                        cost_totals_type[cost_line.id] += temp

                    val_line_values.update(
                        {'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(
                        val_line_values)

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0

                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        cost_totals = cost_totals_type[line.id]

                        if line.split_method == 'by_quantity' and cost_totals.get('total_qty'):
                            per_unit = round(line.price_unit /
                                        cost_totals.get('total_qty'), 9)
                            value = valuation.quantity * per_unit

                        elif line.split_method == 'by_weight' and cost_totals.get('total_weight'):
                            per_unit = (line.price_unit /
                                        cost_totals.get('total_weight'))
                            value = valuation.weight * per_unit

                        elif line.split_method == 'by_volume' and cost_totals.get('total_volume'):
                            per_unit = (line.price_unit /
                                        cost_totals.get('total_volume'))
                            value = valuation.volume * per_unit

                        elif line.split_method == 'equal':
                            value = (line.price_unit /
                                     cost_totals.get('total_line'))

                        elif line.split_method == 'by_current_cost_price' and cost_totals.get('total_cost'):
                            #    per_unit = (line.price_unit / cost_totals.get('total_cost'))
                            #    value = valuation.former_cost * per_unit

                            # elif line.split_method == 'custom' and cost_totals.get('total_cost'):
                            porcent = valuation.former_cost / \
                                cost_totals.get('total_cost')
                            value = line.price_unit * porcent

                        elif line.split_method == 'arancel':
                            if line.move_id.id == valuation.move_id.id:
                                value = line.price_unit

                            else:
                                continue

                        else:
                            value = (line.price_unit / total_line)

                        if digits:
                            value = tools.float_round(
                                value, precision_digits=digits, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value

        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write(
                {'additional_landed_cost': value})

        self.set_cost_summary()
        return True

    def set_cost_summary(self):
        self.cost_summary_ids.unlink()
        group_adj_lines = groupby(
            self.valuation_adjustment_lines, lambda l: l.move_id)

        lines_data = []
        for group, values in group_adj_lines:
            additional_cost = sum([i.additional_landed_cost for i in values])
            adjustment_product = values[0]
            former_cost = adjustment_product.former_cost
            final_cost = former_cost + additional_cost

            lines_data.append(
                (0, 0, {'product_id': adjustment_product.product_id.id,
                        'quantity': adjustment_product.quantity,
                        'former_cost': former_cost,
                        'additional_cost': additional_cost,
                        'final_cost': final_cost,
                        'cost_unit': final_cost / adjustment_product.quantity,
                        }
                 )
            )

        self.cost_summary_ids = lines_data
    
    def button_cancel(self):
        res = super().button_cancel()
        
        for invoice in self.vendor_bill_ids:
            invoice.cost_id = False
            
        return res
        
    @api.model
    def name_get(self):
        result = []

        for stock in self.sudo():
            def _name_get():
                name = stock.name
                ref = self._context.get('display_reference', True)

                if ref:
                    name = '{0} - {1}'.format(stock.name, stock.ref)
                return (stock.id, name)

            result.append(_name_get())
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = [('name', operator, name)]
        if name and self._context.get('display_reference', True):
            domain = ['|',
                      ('name', operator, name),
                      ('ref', operator, name)
                      ]
        return self._search(domain + args, limit=limit,
                            access_rights_uid=name_get_uid)


split_method = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
    ('arancel', 'Arancel')
]


class LandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(split_method)
    arancel_product_id = fields.Many2one('product.product')
    move_id = fields.Many2one('stock.move', string='Movimiento de Existencia')
    account_move_id = fields.Many2one('account.move')


class LandedCostLinesRemove(models.Model):
    _name = 'stock.landed.cost.lines.remove'
    _description = 'Stock Landed Cost Lines Remove'

    cost_id = fields.Many2one('stock.landed.cost', string='Landed Cost')
    picking_id = fields.Many2one('stock.picking', string='Conduce')
    cost_line_id = fields.Many2one('stock.landed.cost.lines', string='Costo')
    product_list_id = fields.Many2one(
        'stock.landed.cost.product.list', string='Product')


class LandedCostProductList(models.Model):
    _name = 'stock.landed.cost.product.list'
    _description = 'Landed Cost Product List'

    name = fields.Char()
    cost_id = fields.Many2one('stock.landed.cost', string='Landed Cost')
    product_id = fields.Many2one('product.product', string='Product')
    arancel = fields.Float(string='Arancel')
    move_id = fields.Many2one('stock.move', string='Movimiento de Existencia')
    picking_id = fields.Many2one(
        'stock.picking', string='Conduce', related='move_id.picking_id')


class LandedCostSummary(models.Model):
    _name = 'stock.landed.cost.summary'
    _description = 'Landed Cost Sumarry'

    cost_id = fields.Many2one('stock.landed.cost', string='Liquidacion')
    product_id = fields.Many2one('product.product', string='Producto')
    product_template = fields.Many2one(
        'product.template', related='product_id.product_tmpl_id')
    quantity = fields.Float(string='Cantidad')
    former_cost = fields.Float(string='Costo de Compras')
    additional_cost = fields.Float(string='Costos Adicionales')
    final_cost = fields.Float(string='Costo Final')
    cost_unit = fields.Float(string='Costo Unid.')
    # porcent_increment = fields.Float(
    #     compute='_compute_porcent_increment',
    #     string='Incremento porcentual',
    # )

    # @api.depends('final_cost', 'former_cost', 'quantity')
    # def _compute_porcent_increment(self):
    #     for record in self:
    #         record.porcent_increment = (record.final_cost * 100
    #                                     / (record.former_cost
    #                                        / (record.quantity if
    #                                           record.quantity else 1))) - 100


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Historial Factor de costo
    cost_history = fields.One2many('stock.landed.cost.summary', 'product_id',
                                   string="Historial de factor de costo")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Historial Factor de costo
    cost_history = fields.One2many('stock.landed.cost.summary', 'product_template',
                                   string="Historial de factor de costo")


class PurchaseInformationLine(models.Model):
    _name = 'purchase.information.line'
    _description = 'Purchase Information Line'

    cost_id = fields.Many2one(
        comodel_name='stock.landed.cost',
        string='Cost',
        required=False)
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
        required=False)
    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase',
        required=False)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        required=False)
    qty_received = fields.Float(
        string='Received Qty', digits='Product Unit of Measure',
        compute="_compute_qty_received_product_qty")
    ordered_qty = fields.Float(string='Ordered Qty', digits='Product Unit of Measure',
                               compute="_compute_qty_received_product_qty")
    amount_total = fields.Monetary(
        string='Total', store=True, related="purchase_id.amount_total")
    currency_id = fields.Many2one('res.currency', 'Currency', store=True,
                                  related="purchase_id.currency_id")

    @api.depends('purchase_id')
    def _compute_qty_received_product_qty(self):

        for rec in self:
            qty_received = 0.0
            ordered_qty = 0.0

            for line in rec.purchase_id.order_line:
                qty_received = qty_received + line.qty_received
                ordered_qty = ordered_qty + line.product_qty

            rec.ordered_qty = ordered_qty
            rec.qty_received = qty_received


class AccountMove(models.Model):
    _inherit = 'account.move'

    cost_id = fields.Many2one(
        comodel_name='stock.landed.cost',
        string='Coste en Destino',
        domain='[("state", "=", "draft")]',
    )

    def action_account_move(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Liquidaciones',
            'res_model': 'stock.landed.cost',
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["id", "=", self.cost_id.id]],
        }

    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)

        res.cost_id.vendor_bill_ids = [(4, res.id)]

        return res

    def write(self, vals):
        last_cost_id = self.cost_id

        res = super(AccountMove, self).write(vals)

        current_cost_id = vals.get('cost_id', False)

        if current_cost_id and current_cost_id != last_cost_id.id:
            last_cost_id.vendor_bill_ids = [(3, self.id, 0)]

            for invoice_line in last_cost_id.cost_lines:
                if invoice_line.account_move_id.id == self.id:
                    invoice_line.unlink()

        if self.cost_id and last_cost_id != self.cost_id:
            self.cost_id.vendor_bill_ids = [(4, self.id)]

            self.cost_id.load_invoices()
            self.cost_id.compute_landed_cost()

        return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    cost_id = fields.Many2one(
        comodel_name='stock.landed.cost'
    )

    def action_purchase_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Liquidaciones',
            'res_model': 'stock.landed.cost',
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["id", "=", self.cost_id.id]],
        }