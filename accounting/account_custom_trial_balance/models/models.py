from odoo import models, _
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
import logging

_logger = logging.getLogger(__name__)

class TrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = super(TrialBalanceCustomHandler, self)._dynamic_lines_generator(report, options, all_column_groups_expression_totals)

        # Add the new column to the options for each section
        for section in range(3):
            new_column = {
                'name': _('Diferencia'),
                'column_group_key': options['columns'][section * 3]['column_group_key'],  # Ensure correct group key
                'expression_label': f'new_column_{section}',
                'class': 'number',
                'figure_type': 'monetary',
                'sortable': False,
                'blank_if_zero': True,
                'style': 'text-align: center; white-space: nowrap;',
            }
            # Insert the new column after the credit column
            options['columns'].insert(section * 3 + 2, new_column)

        # Add your custom logic to calculate the new column values here
        for line in lines:
            # Check if line is a tuple and unpack it
            if isinstance(line, tuple) and len(line) == 2:
                index, line_dict = line
                # Ensure that line_dict is a dict and has 'columns'
                if isinstance(line_dict, dict) and 'columns' in line_dict:
                    for section in range(3):
                        # Verify the length of columns before accessing
                        if len(line_dict['columns']) > section * 3 + 1:
                            # Find debit and credit columns
                            debit_column = line_dict['columns'][section * 3]  # Adjust index based on section
                            credit_column = line_dict['columns'][section * 3 + 1]  # Adjust index based on section

                            # Log the columns being processed to debug
                            _logger.error(f"IMPRIMO SECCION DE FOR {section}")
                            _logger.error(f"IMPRIMO DEBIT COLUMNS {debit_column}")
                            _logger.error(f"IMPRIMO CREDIT COLUMNS {credit_column}")

                            # Ensure debit and credit columns exist and have no_format values
                            debit_value = debit_column['no_format'] if debit_column else 0.0
                            credit_value = credit_column['no_format'] if credit_column else 0.0

                            # Calculate the difference
                            new_column_value = credit_value - debit_value
                            _logger.error(("SOLO IMPIRMOOOOOOOOOOOOOOOOOOOO",line_dict))

                            # Add the calculated value to the new column
                            line_dict['columns'].insert(section * 3 + 2, {
                                'name': self.env['account.report'].format_value(new_column_value, figure_type='monetary'),
                                'class': 'number',
                                'no_format': new_column_value,
                                'style': 'text-align: center; white-space: nowrap;',
                                'expression_label': f'new_column_{section}',
                            })
                            _logger.error((f"LINE DICT AFTER INSERT: {line_dict['columns']}"))

        return lines
