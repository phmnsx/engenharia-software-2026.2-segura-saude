import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "LOG_DATABASE_URL",
    "postgresql://log_writer:log_writer_dev_pass@log-db:5432/segurasaude_logs",
)


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)
