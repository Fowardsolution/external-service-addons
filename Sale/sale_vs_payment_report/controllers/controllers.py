# -*- coding: utf-8 -*-
# from odoo import http


# class PaloSaleReport(http.Controller):
#     @http.route('/palo_sale_report/palo_sale_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/palo_sale_report/palo_sale_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('palo_sale_report.listing', {
#             'root': '/palo_sale_report/palo_sale_report',
#             'objects': http.request.env['palo_sale_report.palo_sale_report'].search([]),
#         })

#     @http.route('/palo_sale_report/palo_sale_report/objects/<model("palo_sale_report.palo_sale_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('palo_sale_report.object', {
#             'object': obj
#         })
