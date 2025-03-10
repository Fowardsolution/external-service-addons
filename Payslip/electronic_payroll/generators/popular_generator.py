# -*- coding: utf-8 -*-

import base64
import io
import logging

from odoo.exceptions import UserError
from .interface import GeneratorInterface

_logger = logging.getLogger(__name__)


class PopularGenerator(GeneratorInterface):
    name = 'Banco Popular'
    code = 'BPD'

    def generate_txt(self, obj):

        full = '{:%Y%m%d}'.format(obj.effective_date)
        rnc = obj.company_id.vat

        seq = obj.env['ir.sequence'].search(
            [('code', '=', self.code),
             ('company_id', '=', obj.company_id.id)], limit=1
        ).number_next_actual
        seq = seq + 1

        file_io = io.BytesIO()

        credit_lines = 0  # cantidad credito / Cuantas Trans. (lineas) se haran.
        amount_credit = 0  # monto credito / El total de Dinero a Trans.

        lines = ''
        position = 1
        for line in obj.line_ids:
            if line.no_file:
                continue
            for rec in line.bank_account_id:
                if rec.bank_name.find('Popular') != -1:
                    employee_id = line.employee_id
                    name = self.remove_accent(employee_id.name)

                    # Eliminamos las siguientes lineas para que no aparezca la cedula en el txt.

                    # Tipo de Documento
                    # RN - RNC
                    # CE - Cedula
                    # PS - Pasaporte
                    # OT - Otro (NUmero de Suplidor, ETC)
                    # doc_type = 'CE'

                    # city_code = employee_id.country_id.code
                    # if not city_code or city_code == 'DO':
                    #    num_doc = employee_id.identification_id
                    #    if not num_doc:
                    #        raise UserError("%s no tiene una Cedula establecida" % employee_id.name)

                    # else:
                    #    num_doc = employee_id.passport_id
                    #    doc_type = 'PS'
                    #    if not num_doc:
                    #       raise UserError("%s no tiene una Pasaporte establecido" % employee_id.name)

                    # num_doc = num_doc.replace(' ', '')
                    credit_lines += 1
                    amount_credit += line.amount

                    bank_account_id = line.bank_account_id

                    account_type = bank_account_id.account_type
                    cod_operation = 22 if account_type == '1' else 32

                    account = str(bank_account_id.acc_number).replace('-', '').zfill(9)

                    amount = str('%.2f' % line.amount).replace('.', '').zfill(13)

                    work_email = employee_id.work_email
                    if work_email:
                        work_email = work_email.ljust(40)

                    send_email = work_email and '1' or ' '

                    linea = "N{rnc}{seq}{posicion}{cuenta}{tipo_cuenta}{moneda}{cod_banco_destino}{digi}{cod_ope}{monto}{nombre}{num_ref}{concepto}{fecha_vencimiento}{forma_contacto}{email_empl}{fax}00{resp_banco}{filler}".format(
                        rnc=str(rnc).ljust(15),
                        seq=str(seq).zfill(7),
                        posicion=str(position).zfill(7),
                        tipo_cuenta=account_type,
                        moneda=214,  # Indique que la moneda es en Peso Dominicano
                        cod_banco_destino=bank_account_id.bank_id.bank_code,
                        digi=bank_account_id.bank_id.bank_digi,
                        cod_ope=cod_operation,
                        cuenta=str(account).ljust(20),
                        filler=''.ljust(52),
                        monto=str(amount).ljust(30),  # Por defecto es 13, si no mostraremos la CE colocamos en 30.
                        # Eliminamos las siguientes 2 lineas para que no aparezca en el txt.
                        # tipoid=doc_type,
                        # id=num_doc.ljust(15),
                        nombre=name.ljust(35)[:35],
                        num_ref=self.description.ljust(12),
                        concepto=''.ljust(40), fecha_vencimiento='    ',
                        forma_contacto=send_email,
                        email_empl=work_email,
                        fax=''.ljust(12), resp_banco=''.ljust(27)

                    )

                    lines += linea + '\r\n'
                    position += 1

        amount_credit = str('%.2f' % amount_credit).replace('.', '').zfill(13)
        credit_lines = str(credit_lines).zfill(11)

        header = 'H{rnc}{nombre}{seq}{tipo}{fec}{cd}{md}{numtrans}{totalapagar}{num_afil}{fec}{email}{resp_banco}{filler}'.format(
            rnc=str(rnc).ljust(15), nombre=obj.company_id.name.ljust(35)[:35],
            seq=str(seq).zfill(7), tipo='01',
            fec=full, cd='00000000000', md='0000000000000',
            totalapagar=amount_credit, numtrans=credit_lines, num_afil='000000000000000',
            email=obj.company_id.electronic_payroll_email, resp_banco=' ',
            filler=''.ljust(136)
        )

        d = '{}\r\n'.format(header)
        file_io.write(str.encode(d))
        file_io.write(str.encode(lines))
        file_value = file_io.getvalue()
        report = base64.encodebytes(file_value)
        file_io.close()

        return report, file_value
