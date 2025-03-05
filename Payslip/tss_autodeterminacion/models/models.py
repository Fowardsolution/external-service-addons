# -*- coding: utf-8 -*-
import xlsxwriter
from io import BytesIO
import base64
import io
import logging

from collections import defaultdict, namedtuple
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SomeModel(models.Model):
    _name = 'some.model'
    _description = 'Modelo Auxiliar para TSS Report'
    
    tss_report_id = fields.Many2one('hr.tss_report', string="TSS Report")
    
class HR_TSSReport(models.Model):
    _name = 'hr.tss_report'
    _description = 'TSS Report'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    dates = fields.One2many('some.model', 'tss_report_id', string="Dates")


class TssReports(models.TransientModel):
    _name = 'hr.tss_report_wizard'
    _description = 'Tss Report Wizard'

    name = fields.Char(string="name", default='Autodeterminacion')
    rnc = fields.Char('RNC o Cedula', readonly=True, default=lambda self: self.env.user.company_id.vat)
    periodo = fields.Char(string='Periodo', readonly=True)
    num_lines = fields.Integer('# de Empleados', compute='_compute_num_lines')
    proceso = fields.Selection([
        ('AM', 'Autodeterminacion Mensual'),
        ('AR', 'Autodeterminacion Retroactiva'),
    ], string='Tipo', default='AM')

    line_ids = fields.One2many('hr.tss_report.lines', 'report_id')

    report_name = fields.Char()
    report = fields.Binary(attachment=True)
    errors = fields.Boolean()
    notes = fields.Text('Notas', readonly=True)

    @api.depends('line_ids')
    def _compute_num_lines(self):
        for r in self:
            r.num_lines = len(r.line_ids)

    def _has_dnot(self, employee_id, month, year):
        try:
            date_from = datetime(year, month, 1)
            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month -= 12
                next_year += 1
            date_to = datetime(next_year, next_month, 1) - timedelta(days=1)
    
            query = """
                SELECT SUM(CASE WHEN hp.credit_note = FALSE THEN pl.total ELSE -pl.total END)
                FROM hr_payslip_line pl
                JOIN hr_payslip hp ON pl.slip_id = hp.id
                WHERE hp.employee_id = %s
                  AND hp.date_from >= %s
                  AND hp.date_to <= %s
            """
            self.env.cr.execute(query, (employee_id, date_from, date_to))
            return self.env.cr.fetchone()[0] or 0
        except ValueError as e:
            raise ValidationError(f"Error en las fechas: {e}")

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        ids = self.env.context.get('active_ids', [])
        run_ids = self.env['hr.payslip.run'].browse(ids)

        dates = []
        for i in run_ids:
            dates.append(str(i.date_start)[:8])
            dates.append(str(i.date_end)[:8])

        if len(set(dates)) > 1:
            msg = 'El periodo de las Nominas seleccionadas no es el mismo.'
            raise UserError(msg)

        return super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    @api.onchange('rnc')
    def onchange_rnc(self):
        # Notar: se recorren los registros del wizard (no se accede a un campo 'employee_id' en este nivel)
        # Si se requiere iterar sobre líneas, se debería recorrer self.line_ids
        tags = self.env['hr.tss_report.tags'].search([])
        tss_columns = {i.id: i.code for i in tags}
        get_gender = {'male': 'M', 'female': 'F'}

        employee_obj = self.env['hr.employee']

        run_ids = self.env.context.get('active_ids', [])

        query = """
          SELECT e.id, e.identification_id, e.passport_id, e.birthday, COALESCE(c.code, 'DO') as pais, e.gender, 
            rt.tag_id as columna, SUM(pl.total) as monto
            FROM hr_payslip_line AS pl
            INNER JOIN hr_salary_rule AS sr ON pl.salary_rule_id = sr.id 
            INNER JOIN hr_payslip AS ps ON ps.id = pl.slip_id 
            INNER JOIN hr_employee AS e ON e.id = ps.employee_id
            INNER JOIN rule_tag_rel AS rt ON rt.rule_id = sr.id
            FULL JOIN res_country AS c ON c.id = e.country_id
            WHERE pl.slip_id IN (
                SELECT id FROM hr_payslip WHERE payslip_run_id IN %s
            ) AND sr.tss_report = TRUE AND pl.total > 0 
            GROUP BY e.id, rt.tag_id, c.code, e.identification_id, e.passport_id, e.birthday, e.gender
        """

        self.env.cr.execute(query, (tuple(run_ids),))
        query_data = namedtuple('Line', 'employee_id, cedula, pasaporte, birthday, pais, genero, columna, monto')
        lines_data = [query_data._make(i) for i in self.env.cr.fetchall()]

        # Se asume que al menos un payslip run existe
        dates = self.env['hr.payslip.run'].browse(run_ids[0]).mapped('date_start')

        data_lines = {}
        lines = []
        for line in lines_data:
            if not line.columna:
                continue

            if line.employee_id not in data_lines:
                data_lines[line.employee_id] = defaultdict(float)
                data_lines[line.employee_id]['employee_id'] = line.employee_id

                # Si la consulta no trae company_id, se usa la compañía actual
                company = getattr(line, 'company_id', self.env.company)
                clave_nomina = "{:03}".format(int(company.nomina_key)) if company.nomina_key else '000'

                if not line.pais or line.pais == 'DO':
                    data_lines[line.employee_id]['tipo_doc'] = 'C'

                    cedula = ''
                    if line.cedula:
                        cedula = '{:0>11.11}'.format(line.cedula.replace('-', ''))
                    data_lines[line.employee_id]['numero_doc'] = cedula or ''
                else:
                    data_lines[line.employee_id]['tipo_doc'] = 'P'
                    data_lines[line.employee_id]['numero_doc'] = line.pasaporte or ''

                data_lines[line.employee_id]['gender'] = get_gender.get(line.genero, '')
                data_lines[line.employee_id]['clave_nomina'] = clave_nomina
                data_lines[line.employee_id]['birth_day'] = line.birthday
                data_lines[line.employee_id]['tipo_ingreso'] = '0001'

                has_dnot = self._has_dnot(line.employee_id, dates[0].month, dates[0].year)
                if has_dnot:
                    data_lines[line.employee_id]['tipo_ingreso'] = '0004'

            data_lines[line.employee_id][tss_columns.get(line.columna)] += line.monto

        for i in data_lines.values():
            lines.append((0, 0, dict(i)))

        periodo = '{}{:02}'.format(dates[0].year, dates[0].month)
        self.periodo = periodo
        self.line_ids = lines
        self.rnc = self.env.user.company_id.vat
        self.validation()

    def get_message(self, error, lines):
        message = False
        self.errors = error
        if error:
            message = 'Clic en el nombre del empleado para acceder al mismo<br/>{}'.format(lines)
        return message

    def validation(self):
        _action_url = '/web#id={}&view_type=form&model=hr.employee'
        error = False

        lines = ''
        for l in self.line_ids:
            _url = _action_url.format(l.employee_id.id)

            if not l.numero_doc:
                error = True
                val = 'No tiene Numero de Documento'
                lines += "<a target='_blank' href='{}'>{}</a> {}<br/>".format(_url, l.employee_id.name, val)

            if l.tipo_doc != 'C':
                if not l.employee_id.nombres:
                    error = True
                    val = 'No tiene configurado el/los Nombre(s) en su ficha en el apartado [info TSS]'
                    lines += "<a target='_blank' href='{}'>{}</a> {}<br/>".format(_url, l.employee_id.name, val)

                if not l.employee_id.apellido_paterno:
                    error = True
                    val = 'No tiene configurado el Apellido Paterno en su ficha en el apartado [info TSS]'
                    lines += "<a target='_blank' href='{}'>{}</a> {}<br/>".format(_url, l.employee_id.name, val)

                if not l.employee_id.apellido_materno:
                    error = True
                    val = 'No tiene configurado el Apellido Materno en su ficha en el apartado [info TSS]'
                    lines += "<a target='_blank' href='{}'>{}</a> {}<br/>".format(_url, l.employee_id.name, val)

                if not l.employee_id.birthday:
                    error = True
                    val = 'No tiene configurado la fecha de nacimiento'
                    lines += "<a target='_blank' href='{}'>{}</a> {}<br/>".format(_url, l.employee_id.name, val)

                if not l.employee_id.gender:
                    error = True
                    val = 'No tiene configurado el genero'
                    lines += "<a target='_blank' href='{}'>{}</a> {}<br/>".format(_url, l.employee_id.name, val)

        self.notes = self.get_message(error, lines)

    def generate_txt(self):
        def format_value(value, lon=0, remove_dash=False):
            if isinstance(value, bool):
                value = ''

            if isinstance(value, str) :
                if remove_dash:
                    value = value.replace('-', '').replace('_', '').replace(' ', '')
                return '{:{space}.{max}}'.format(value, space=lon, max=lon)

            elif isinstance(value, float) or isinstance(value, int):
                return '{:0>16.2f}'.format(value)

        run_ids = self.env.context.get('active_ids', [])
        dates = self.env['hr.payslip.run'].browse(
            run_ids[0]).mapped('date_start')
        periodo = dates[0]
        periodo = '{:02}{}'.format(periodo.month, periodo.year)
        self.periodo = periodo

        self.notes = ''
        self.validation()
        
        modal = {
            'context': self.env.context,
            'view_mode': 'form',
            'res_model': 'hr.tss_report',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

        if self.errors:
           return modal

        tmpl = 'D{clave_nomina}{tipo_doc}{numero_doc}{nombres}{ap}{am}\
{gender}{birth_day}{salario_cotizable}{aporte_voluntario}{salario_isr}\
{otro_remuneracion}{id_agente}{rem_otro_agentes}{ing_exentos}{saldo_favor}\
{infotep}{tipo_ingreso}\n'

        lines = ''
        for l in self.line_ids:
            fecha = fields.Date.from_string(l.birth_day)
            birth_day = '{:%d%m%Y}'.format(fecha) if fecha else '        '

            nombres = l.employee_id.nombres or ' '
            ap = l.employee_id.apellido_paterno or ' '
            am = l.employee_id.apellido_materno or ' '

            vals = {
                'clave_nomina': '{:0>3.3}'.format(l.clave_nomina),
                'tipo_doc': l.tipo_doc,
                'numero_doc': format_value(l.numero_doc, 25, True),
                'nombres': format_value(nombres, 50),
                'ap': format_value(ap, 40),
                'am': format_value(am, 40),
                'gender': l.gender,
                'birth_day': birth_day,
                'salario_cotizable': format_value(l.salario_cotizable),
                'aporte_voluntario': format_value(l.aporte_voluntario),
                'salario_isr': format_value(l.salario_isr),
                'otro_remuneracion': format_value(l.otro_remuneracion),
                'id_agente': format_value(l.id_agente, 11),
                'rem_otro_agentes': format_value(l.rem_otro_agentes),
                'ing_exentos': format_value(l.ing_exentos),
                'saldo_favor': format_value(l.saldo_favor),
                'infotep': format_value(l.infotep),
                'tipo_ingreso': l.tipo_ingreso,
            }

            lines += tmpl.format(**vals)

        f = io.BytesIO()
        f.write(str.encode('E{o.proceso}{o.rnc:>11}{o.periodo}\n'.format(o=self)))
        f.write(str.encode(lines))
        f.write(str.encode('S{:0>6}'.format(self.num_lines + 2)))

        report = base64.b64encode(f.getvalue())
        f.close()

        report_name = '{}_{}.txt'.format(self.rnc, self.periodo)
        self.write({'report': report, 'report_name': report_name})
        return modal

    def generate_excel(self):
        # Crear el archivo Excel en memoria
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('TSS Report')
    
        # Formato para las celdas
        bold = workbook.add_format({'bold': True})
        cell_format = workbook.add_format({'num_format': '#,##0.00'})
    
        # Encabezados de columnas
        headers = [
            'Clave Nomina', 'Tipo Documento', 'Numero Documento', 'Nombres',
            '1er. Apellido', '2do. Apellido', 'Genero', 'Fecha Nacimiento', 'Salario Cotizable', 'Aporte Voluntario',
            'Salario ISR',  'Tipo de Ingreso', 'Otras Remuneraciones', 'RNC/Ced. Agente Ret.',
            'Remuneracion Otros Agentes', 'Saldo a Favor', 'Ingresos Exentos', 'Preavisos, Cesantia',
            'Retencion Pension', 'Infotep',
        ]
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)
    
        # Diccionario de selección para tipo_ingreso
        tipo_ingreso_dict = dict(self.env['hr.tss_report.lines']._fields['tipo_ingreso'].selection)
    
        # Ordenar las líneas por el nombre del empleado
        sorted_lines = sorted(self.line_ids, key=lambda l: l.employee_id.nombres or '')
    
        row_num = 1
        for line in sorted_lines:
            worksheet.write(row_num, 0, line.clave_nomina or '', cell_format)
            worksheet.write(row_num, 1, line.tipo_doc or '', cell_format)
            worksheet.write(row_num, 2, line.numero_doc or '', cell_format)
            worksheet.write(row_num, 3, line.employee_id.nombres or '', cell_format)
            worksheet.write(row_num, 4, line.employee_id.apellido_paterno or '', cell_format)
            worksheet.write(row_num, 5, line.employee_id.apellido_materno or '', cell_format)
            worksheet.write(row_num, 6, line.gender or '', cell_format)
            worksheet.write(row_num, 7, line.birth_day.strftime('%d%m%Y') if line.birth_day else '', cell_format)
            worksheet.write(row_num, 8, line.salario_cotizable or 0.0, cell_format)
            worksheet.write(row_num, 9, line.aporte_voluntario or 0.0, cell_format)
            worksheet.write(row_num, 10, line.salario_isr or 0.0, cell_format)
            worksheet.write(row_num, 11, tipo_ingreso_dict.get(line.tipo_ingreso, ''), cell_format)
            worksheet.write(row_num, 12, line.otro_remuneracion or 0.0, cell_format)
            worksheet.write(row_num, 13, line.id_agente or '', cell_format)
            worksheet.write(row_num, 14, line.rem_otro_agentes or 0.0, cell_format)
            worksheet.write(row_num, 15, line.saldo_favor or 0.0, cell_format)
            worksheet.write(row_num, 16, line.ing_exentos or 0.0, cell_format)
            # Notar: Se debe ajustar la escritura de las columnas 17 y 18 si se requiriera.
            worksheet.write(row_num, 19, line.infotep or 0.0, cell_format)
            row_num += 1
    
        workbook.close()
        output.seek(0)
    
        excel_data = base64.b64encode(output.read()).decode('utf-8')
    
        attachment = self.env['ir.attachment'].create({
            'name': 'TSS_Report.xlsx',
            'type': 'binary',
            'datas': excel_data,
            'store_fname': 'TSS_Report.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
    
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

class TssReportLines(models.TransientModel):
    _name = 'hr.tss_report.lines'
    _description = 'Tss Report Lines'

    report_id = fields.Many2one('hr.tss_report_wizard')
    clave_nomina = fields.Char(string='Clave Nomina', default='001')  # Se eliminó "size" (deprecado en v17)
    tipo_doc = fields.Selection([('C', 'Cedula'),
                                 ('N', 'NSS'),
                                 ('P', 'Pasaporte')], string='Tipo Doc.')
    numero_doc = fields.Char(string='Numero Documento')
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    gender = fields.Selection([('M', 'Masculino'),
                               ('F', 'Femenino'),
                               ('', 'No Definido')], string='Genero')
    birth_day = fields.Date(string='Fecha Nacimiento')
    salario_cotizable = fields.Float(string='Salario Cotizable')
    aporte_voluntario = fields.Float(string='Aporte Voluntario')
    salario_isr = fields.Float(string='Salario ISR')
    otro_remuneracion = fields.Float(string='Otras Remuneraciones')
    id_agente = fields.Char(string='RNC/Ced. Agente Ret.')
    rem_otro_agentes = fields.Float(string='Remuneracion Otros Agentes')
    ing_exentos = fields.Float(string='Ingresos Exentos del Periodo')
    saldo_favor = fields.Float(string='Saldo a Favor del Periodo')
    infotep = fields.Float(string='Infotep')
    tipo_ingreso = fields.Selection([
        ('0001', 'Normal'),
        ('0002', 'Trabajador ocasional (no fijo)'),
        ('0003', 'Asalariado por hora o labora tiempo parcial'),
        ('0004', 'No laboró mes completo por razones varias'),
        ('0005', 'Salario prorrateado semanal/bisemanal'),
        ('0006', 'Pensionado antes de la Ley 87-01'),
        ('0007', 'Exento por Ley de pago al SDSS'),
    ], string='Tipo de Ingreso', default='0001')


class TssReportTags(models.Model):
    _name = 'hr.tss_report.tags'
    _description = 'TSS Report TAGS'
    _order = 'sequence'

    name = fields.Char('Nombre')
    code = fields.Char('Codigo')
    sequence = fields.Integer('sequence')

    rule_ids = fields.Many2many('hr.salary.rule', 'rule_tag_rel', 'tag_id', 'rule_id')


class TSSTipoNomina(models.Model):
    _name = "tss.tipo_nomina"
    _description = 'TSS Tipo Nomina'

    name = fields.Char(string="Nombre")
    code = fields.Char(string="Code", help='Codigo de Identificacion Suministrado por la TSS')


class ResCompany(models.Model):
    _inherit = "res.company"

    nomina_key = fields.Char(string="Clave TSS Nómina", help='Codigo de Identificacion Suministrado por la TSS')

    @api.model
    def get_values(self):
        res = super(ResCompany, self).get_values()
        res.update({'nomina_key': self.env.company.nomina_key})
        return res
