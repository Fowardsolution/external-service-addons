from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Partner(models.Model):
    _inherit = 'res.partner'

    same_phone_partner = fields.Many2one(
        comodel_name='res.partner',
        string='Contacto con mismo número teléfonico',
        compute='_compute_same_phone_partner', store=False)

    @api.depends('vat')
    def _compute_same_vat_partner_id(self):
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            domain = [('vat', '=', partner.vat)]
            if partner_id:
                domain += [('id', '!=', partner_id), '!',
                           ('id', 'child_of', partner_id)]
            partner.same_vat_partner_id = bool(partner.vat) and not \
                partner.parent_id and self.env['res.partner'].search(
                domain, limit=1)
            partner_name = partner.same_vat_partner_id.name
            if partner.same_phone_partner:
                raise ValidationError("Ya existe un contacto con este correo: "
                                      "%s" % partner_name)

    @api.depends('mobile')
    def _compute_same_phone_partner(self):
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            domain = [('mobile', '=', partner.mobile)]
            if partner_id:
                domain += [('id', '!=', partner_id), '!',
                           ('id', 'child_of', partner_id)]
            partner.same_phone_partner = bool(partner.mobile) and not \
                partner.parent_id and self.env['res.partner'].search(
                domain, limit=1)
            partner_name = partner.same_phone_partner.name
            if partner.same_phone_partner:
                raise ValidationError("Ya existe un contacto con este numero "
                                      "y/o correo: %s" % partner_name)


