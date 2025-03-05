# -*- coding: utf-8 -*-

import base64
import io
import logging

from .interface import GeneratorInterface

_logger = logging.getLogger(__name__)

class BHDTemplate(GeneratorInterface):
    name = 'Banco BHD'
    code = 'BHD'

    def generate_txt(self, obj):
        file_io = io.BytesIO()
        lines = []

        for line in obj.line_ids:
            if line.no_file:
                continue
            for rec in line.bank_account_id:
                bank_name = rec.bank_name or ''  # Evita errores si es None
                if 'BHD' in bank_name:  
                    name = self.remove_accent(line.employee_id.name)

                    account = line.bank_account_id.acc_number.replace('-', '').zfill(9)
                    amount = '{:.2f}'.format(float(line.amount)).replace('.', '').zfill(13)  # Formato seguro
                    
                    # Uso correcto de `\r\n` para archivos TXT en Windows/Linux
                    lines.append(f"{account};{name};{line.employee_id.id};{amount};{self.description};\r\n")

        file_io.write("".join(lines).encode())  # Escribe todo en un solo paso

        report_value = file_
