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
        full_date = obj.effective_date.strftime('%Y%m%d')
        rnc = obj.company_id.vat or "00000000000"  # Evita errores si el RNC está vacío

        # Obtener secuencia de la compañía
        sequence = obj.env['ir.sequence'].search(
            [('code', '=', self.code), ('company_id', '=', obj.company_id.id)], limit=1
        )
        seq = (sequence.number_next_actual if sequence else 0) + 1

        file_io = io.BytesIO()
        lines = []
        credit_lines = 0
        amount_credit = 0

        position = 1
        for line in obj.line_ids:
            if line.no_file:
                continue

            bank_account = line.bank_account_id
            if not bank_account:
                continue

            employee_id = line.employee_id
            name = self.remove_accent(employee_id.name)

            # Determinar el tipo de cuenta bancaria
            account_type = bank_account.account_type
            cod_operation = 22 if account_type == '1' else 32

            account = bank_account.acc_number.replace('-', '').zfill(9)
            amount = '{:.2f}'.format(line.amount).replace('.', '').zfill(13)

            work_email = employee_id.work_email or ""
            work_email = work_email.ljust(40)[:40]
            send_email = '1' if work_email.strip() else ' '

            # Línea de transacción
            linea = (
                f"N{rnc.ljust(15)}{str(seq).zfill(7)}{str(position).zfill(7)}"
                f"{account_type}214{bank_account.bank_id.bank_code}{bank_account.bank_id.bank_digi}"
                f"{cod_operation}{account.ljust(20)}{amount.ljust(30)}"
                f"{name.ljust(35)[:35]}{self.description.ljust(12)}{''.ljust(40)}    "
                f"{send_email}{work_email}{''.ljust(12)}00{''.ljust(27)}{''.ljust(52)}\r\n"
            )
            lines.append(linea)

            credit_lines += 1
            amount_credit += line.amount
            position += 1

        # Formatear valores finales
        amount_credit = '{:.2f}'.format(amount_credit).replace('.', '').zfill(13)
        credit_lines = str(credit_lines).zfill(11)

        # Encabezado del archivo
        header = (
            f"H{rnc.ljust(15)}{obj.company_id.name.ljust(35)[:35]}"
            f"{str(seq).zfill(7)}01{full_date}00000000000"
            f"0000000000000{amount_credit}{credit_lines}000000000000000"
            f"{obj.company_id.electronic_payroll_email or ''} {''.ljust(136)}\r\n"
        )

        # Escribir en el archivo
        file_io.write(header.encode())
        file_io.write("".join(lines).encode())

        file_value = file_io.getvalue()
        report = base64.b64encode(file_value)  # Manejo seguro de base64

        file_io.close()
        return report, file_value
