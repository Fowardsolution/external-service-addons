# -*- coding: utf-8 -*-

import base64
import io
import logging

from .interface import GeneratorInterface

_logger = logging.getLogger(__name__)

class BDRTemplate(GeneratorInterface):
    name = 'Banco del Reservas'
    code = 'BDR'

    def generate_txt(self, obj):
        file_io = io.BytesIO()
        lines = []

        origin_account = obj.origin_account or "000000000"  # Evita errores si está vacío

        for line in obj.line_ids:
            if line.no_file:
                continue

            account = line.bank_account_id.acc_number.replace('-', '').zfill(9)
            amount = '{:.2f}'.format(float(line.amount)).replace('.', '').zfill(13)  # Formato seguro

            identification_id = (line.employee_id.identification_id or "").replace('-', '').zfill(11)  # Evita errores si es None
            
            # Formato de salida correcto con `\r\n`
            lines.append(f"{origin_account},{account},{amount},{identification_id}\r\n")

        file_io.write("".join(lines).encode())  # Escribe todo en un solo paso

        report_value = file_io.getvalue()
        report = base64.b64encode(report_value)  # Mejor compatibilidad

        file_io.close()

        return report, report_value
