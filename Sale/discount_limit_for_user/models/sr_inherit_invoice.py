# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError


class srAccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    @api.onchange('discount')
    def check_discount_limit(self):
        if self.env.user.discount_limit != 0.00 and self.discount > self.env.user.discount_limit:
            message = "Solo puedes asignar máximo " + str(self.env.user.discount_limit) + "% de descuento \nComuníquese con su administrador para obtener más detalles."
            raise ValidationError(_(message))
    
    @api.constrains('discount')
    def check_discount_limit_constrains(self):
        for record in self:
            if self.env.user.discount_limit != 0.00 and record.discount > self.env.user.discount_limit:
                message = "Solo puedes asignar máximo " + str(self.env.user.discount_limit) + "% de descuento \nComuníquese con su administrador para obtener más detalles."
                raise ValidationError(_(message))

