# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

import logging

_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    increment_rate = fields.Float()


class ResCurrencyUpdate(models.Model):
    _name = 'res.currency.update'

    def update_currency_rate(self):
        company_id = self.env['res.company'].search([])
        url = 'https://www.infodolar.com.do/precio-dolar-entidad-banco-popular.aspx'
        # if currency_eur:
        #     url = 'https://www.infodolar.com.do/precio-euro-entidad-banco-popular.aspx'
        current_company = self.env.company
        current_currency = current_company.currency_id
        response = requests.get(url)

        # Verificar que la solicitud fue exitosa
        if response.status_code == 200:
            # Crear un objeto BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            # Encontrar la tabla que contiene los datos
            table = soup.find('table', id="Entidad")  # Encuentra la primera tabla en la página
            # print(table)

            # Encontrar todas las filas de la tabla
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    # Encontrar todas las celdas en la fila
                    cells = row.find_all('td', class_='colCompraVenta')
                    # print(cells)
                    # Asegurarse de que hay celdas en la fila
                    if cells:
                        # Extraer el valor de compra y venta
                        buy_value = cells[0].text.strip().replace('$', '').replace(',', '')[:6].strip()
                        sell_value = cells[1].text.strip().replace('$', '').replace(',', '')[:6].strip()
                        for rec in company_id:
                            _logger.error(("ASDASDAS", rec))
                            if rec.currency_id.name == 'DOP':
                                tz = pytz.timezone('America/Santo_Domingo')
                                ahora_utc = datetime.now(pytz.utc)
                                hora_santo_domingo = ahora_utc.astimezone(tz).date()
                                currency_usd = rec.env['res.currency'].search([('name', '=', 'USD')])
                                date_rate = rec.env['res.currency.rate'].search(
                                    [('name', '=', hora_santo_domingo), ('company_id', '=', rec.id)])
                                _logger.error(("VALUE", currency_usd.increment_rate))

                                if not date_rate:
                                    date_rate.sudo().create({
                                        'name': fields.Date.today(),
                                        'company_id': rec.id,
                                        'inverse_company_rate': float(sell_value) + currency_usd.increment_rate,
                                        'currency_id': currency_usd.id,
                                    })


            else:
                _logger.error(("No se encontró la tabla en la página."))
        else:
            _logger.error((f'Error al acceder a la página: {response.status_code}'))
