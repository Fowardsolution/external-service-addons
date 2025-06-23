# -- coding: utf-8 -*-

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_landed = fields.Boolean()

    def button_validate(self):
        """
        button validate.
        """
        res = super(StockPicking, self).button_validate()
        self.is_landed = True

        return res

    def action_create_landed_cost(self):
        if self.is_landed:
            return {
                'warning': {
                    'title': 'Advertencia',
                    'message': 'Ya se ha generado un coste en destino para esta transferencia.',
                }
            }
    
        landed_cost = self.env['stock.landed.cost'].create({
            'picking_ids': [self.id]
        })
    
        self.is_landed = False
    
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Coste en Destino',
            'view_mode': 'form',
            'res_model': 'stock.landed.cost',
            'target': 'current',
            'res_id': landed_cost.id,
        }
    
        return action
