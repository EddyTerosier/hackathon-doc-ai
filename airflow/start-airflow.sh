#!/bin/sh
set -eu

PASSWORD_FILE="/opt/airflow/simple_auth_manager_passwords.json.generated"

printf '{"admin": "admin"}\n' > "$PASSWORD_FILE"

exec airflow standalone
