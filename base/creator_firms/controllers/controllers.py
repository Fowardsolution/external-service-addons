# -*- coding: utf-8 -*-
# from odoo import http


# class CreatorFirms(http.Controller):
#     @http.route('/creator_firms/creator_firms/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/creator_firms/creator_firms/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('creator_firms.listing', {
#             'root': '/creator_firms/creator_firms',
#             'objects': http.request.env['creator_firms.creator_firms'].search([]),
#         })

#     @http.route('/creator_firms/creator_firms/objects/<model("creator_firms.creator_firms"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('creator_firms.object', {
#             'object': obj
#         })
