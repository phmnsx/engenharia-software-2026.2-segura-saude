import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app_user:app_user_dev_pass@metadados-db:5432/segurasaude",
)


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)
