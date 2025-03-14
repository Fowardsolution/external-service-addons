import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate_invoice_payment(env):
    """
    invoice_payment_state   ---->   payment_date
    """
    env.cr.execute(
        """
        SELECT EXISTS(
            SELECT
            FROM information_schema.columns
            WHERE table_name = 'account_move'
            AND column_name = 'invoice_payment_state'
        );
        """
    )
    if env.cr.fetchone()[0] or False:
        query = """
        UPDATE account_move
        SET payment_state = invoice_payment_state;
        """
        _logger.info(
            """
            Migrating fields:
            invoice_payment_state   ---->   payment_state
            """
        )
        env.cr.execute(query)

        _logger.info("Dropping account_move deprecated columns")
        drop_query = """
        ALTER TABLE account_move
        DROP COLUMN IF EXISTS invoice_payment_state,
        DROP COLUMN IF EXISTS cancellation_type;
        """
        env.cr.execute(drop_query)


def migrate(cr, version):

    env = api.Environment(cr, SUPERUSER_ID, {})
    # migrate_ref_field(env)
    migrate_invoice_payment(env)
    # drop_sequence_fields(env)
