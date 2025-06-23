# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WizardCostListRemove(models.TransientModel):
    _name = 'wizard.cost.list.remove'
    _description = 'Wizard Cost List remove'

    picking_id = fields.Many2one('stock.picking', string='Conduce')
    cost_line_id = fields.Many2many('stock.landed.cost.lines')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(WizardCostListRemove, self).fields_get(allfields, attributes)

        active_id = self.env.context.get('active_id', [])
        picking_ids = self.env['stock.landed.cost'].browse(active_id).picking_ids.ids
        res['picking_id']['domain'] = [('id', 'in', picking_ids)]

        cost_lines = self.env['stock.landed.cost.lines'].search([
            ('cost_id', '=', active_id),('arancel_product_id', '=', False)
        ])
        res['cost_line_id']['domain'] = [('id', 'in', [c.id for c in cost_lines])]

        return res

    def action_remove_cost_line(self):
        active_id = self.env.context.get('active_id', [])

        remove_cost = self.env['stock.landed.cost.lines.remove']
        landed_cost = self.env['stock.landed.cost'].browse(active_id)

        remove_cost.search([
            ('cost_id', '=', landed_cost.id), ('picking_id', '=', self.picking_id.id)
        ]).unlink()

        for line in landed_cost.product_list_ids.filtered(
                lambda l: l.picking_id.id == self.picking_id.id):
            for cost in self.cost_line_id:
                remove_cost.create({
                    'product_list_id': line.id,
                    'cost_id': landed_cost.id,
                    'cost_line_id': cost.id,
                    'picking_id': self.picking_id.id,
                })
