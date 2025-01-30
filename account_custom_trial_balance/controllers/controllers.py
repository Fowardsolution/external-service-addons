# from odoo import http
# from odoo.http import request
#
# class CustomTrialBalanceController(http.Controller):
#     @http.route('/custom_trial_balance/update_balance', type='http', auth='user')
#     def update_balance(self, line, debit_column_key, credit_column_key, total_diff_values_key):
#         handler = request.env['account.trial.balance.report.handler']
#         handler.custom_update_balance_columns(line, debit_column_key, credit_column_key, total_diff_values_key)
#         return {'status': 'success'}