import xlsxwriter
from io import BytesIO
import base64
import logging
from collections import defaultdict
from odoo import fields, models, _

_logger = logging.getLogger(__name__)

class PrintPayslipBatches(models.TransientModel):
    _name = 'export.payslip.batches.details.xls'
    _description = 'Export Payslip Batches'

    excel_file = fields.Binary(string='Excel File')
    payslip_batches_ids = fields.Many2many('hr.payslip.run', string='Payslip Batches')

    def get_code_list(self, payslip_ids):
        lst = []
        if payslip_ids:
            sql_query = """SELECT DISTINCT psl.salary_rule_id as rule_id 
                           FROM hr_payslip_line as psl 
                           JOIN hr_payslip as ps ON ps.id = psl.slip_id 
                           JOIN hr_salary_rule as salaryrule ON psl.salary_rule_id = salaryrule.id  
                           WHERE ps.id IN %s AND salaryrule.appears_on_payslip = 't'"""
            params = (tuple(payslip_ids),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            rule_ids = [line['rule_id'] for line in results]
            sorted_rules = self.env['hr.salary.rule'].browse(rule_ids).sorted(key=lambda r: r.sequence)
            lst = [rule.code for rule in sorted_rules]
        return lst

    def print_excel(self):
        filename = 'Nomina detallada.xlsx'
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        worksheet = workbook.add_worksheet('Payslip Details')

        # Formatos
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 12})
        label_format = workbook.add_format({'bold': True, 'bg_color': '#b0bec5'})
        label_format_dept = workbook.add_format({'bold': True, 'bg_color': '#eceff1'})
        num_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        line_format = workbook.add_format({'bottom': 2, 'bottom_color': 'black'})


        # Configuración
        worksheet.set_column(0, 0, 5)  # No.
        worksheet.set_column(1, 1, 40)  # Nombre empleado
        worksheet.set_column(2, 2, 25)  # Puesto de trabajo
        worksheet.set_column(3, 3, 20)  # Identificación

        worksheet.merge_range(0, 2, 1, 6, 'DETALLES DE NÓMINA', header_format)

        if self.payslip_batches_ids:
            min_date = min(batch.date_start for batch in self.payslip_batches_ids)
            max_date = max(batch.date_end for batch in self.payslip_batches_ids)
            period_text = f"Período: {min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}"
            worksheet.merge_range(2, 2, 2, 6, period_text, header_format)

        worksheet.write('A4', 'No.', label_format)
        worksheet.write('B4', 'Nombre empleado', label_format)
        worksheet.write('C4', 'Puesto de trabajo', label_format)
        worksheet.write('D4', 'Identificación', label_format)

        payslip_ids = []
        grouped_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        for batch in self.payslip_batches_ids:
            for slip in batch.slip_ids:
                dept = slip.employee_id.department_id.name
                emp = slip.employee_id
                payslip_ids.append(slip.id)
                for line in slip.line_ids:
                    grouped_data[dept][emp][line.code] += line.total

        code_list = self.get_code_list(payslip_ids)
        col_counter = 4
        for code in code_list:
            worksheet.set_column(col_counter, col_counter, 12)
            worksheet.write(3, col_counter, code, label_format)
            col_counter += 1

        row_counter = 4
        total_general = {code: 0.0 for code in code_list}

        for dept, employees in grouped_data.items():
            worksheet.merge_range(row_counter, 0, row_counter, 3, f'Departamento: {dept}', label_format_dept)
            row_counter += 1
            dept_totals = {code: 0.0 for code in code_list}
            line_no = 1

            for emp, payslip_data in employees.items():
                worksheet.write(row_counter, 0, line_no)
                worksheet.write(row_counter, 1, emp.name or '')
                worksheet.write(row_counter, 2, emp.job_title or '')
                worksheet.write(row_counter, 3, emp.identification_id or '')

                col_counter = 4
                for code in code_list:
                    amount = payslip_data.get(code, 0.0)
                    dept_totals[code] += amount
                    total_general[code] += amount
                    worksheet.write_number(row_counter, col_counter, amount, num_format)
                    col_counter += 1

                row_counter += 1
                line_no += 1

            worksheet.write(row_counter, 1, f'Total - {dept}', line_format)
            col_counter = 4
            for code in code_list:
                worksheet.write_number(row_counter, col_counter, dept_totals[code], num_format)
                col_counter += 1
            row_counter += 2

        worksheet.merge_range(row_counter, 0, row_counter, 3, 'TOTAL GENERAL', line_format)
        col_counter = 4
        for code in code_list:
            worksheet.write_number(row_counter, col_counter, total_general[code], num_format)
            col_counter += 1

        workbook.close()
        fp.seek(0)
        self.excel_file = base64.b64encode(fp.read())
        fp.close()

        url = f'/web/content/?model=export.payslip.batches.details.xls&field=excel_file&id={self.id}&filename={filename}'
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}
