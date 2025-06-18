# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    restrict_locations = fields.Boolean(string='Restringir ubicación')

    stock_location_ids = fields.Many2many(
        comodel_name='stock.location',
        relation='location_security_stock_location_users',
        column1='user_id',
        column2='location_id',
        string='Ubicaciones de existencias',
    )

    default_picking_type_ids = fields.Many2many(
        comodel_name='stock.picking.type',
        relation='stock_picking_type_users_rel',
        column1='user_id',
        column2='picking_type_id',
        string='Operaciones de almacén predeterminadas',
    )


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.constrains('state', 'location_id', 'location_dest_id')
    def _check_user_location_rights(self):
        for move in self:
            # Skip draft moves
            if move.state == 'draft':
                continue

            user = self.env.user
            if user.restrict_locations:
                allowed_locations = user.stock_location_ids
                msg = _(
                    'Ubicación no válida. No puedes procesar esta mudanza porque no '
                    'no controlar la ubicación "%s". Por favor, póngase en contacto con su administrador.'
                )
                if move.location_id not in allowed_locations:
                    raise UserError(msg % move.location_id.name)
                if move.location_dest_id not in allowed_locations:
                    raise UserError(msg % move.location_dest_id.name)