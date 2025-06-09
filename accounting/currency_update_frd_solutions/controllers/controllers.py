# -*- coding: utf-8 -*-
# from odoo import http


# class CurrencyUpdateFrdSolutions(http.Controller):
#     @http.route('/currency_update_frd_solutions/currency_update_frd_solutions', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/currency_update_frd_solutions/currency_update_frd_solutions/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('currency_update_frd_solutions.listing', {
#             'root': '/currency_update_frd_solutions/currency_update_frd_solutions',
#             'objects': http.request.env['currency_update_frd_solutions.currency_update_frd_solutions'].search([]),
#         })

#     @http.route('/currency_update_frd_solutions/currency_update_frd_solutions/objects/<model("currency_update_frd_solutions.currency_update_frd_solutions"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('currency_update_frd_solutions.object', {
#             'object': obj
#         })
