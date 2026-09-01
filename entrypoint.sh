#!/bin/sh
set -e
DB=$(echo "${DATABASE_URL:-sqlite:////data/db.sqlite3}" | sed 's|sqlite:///*|/|')
if [ ! -s "$DB" ]; then
    echo "Banco novo: aplicando migrations..."
    python manage.py migrate --noinput
    python manage.py migrate --database=vault --noinput
else
    echo "Banco existente detectado; iniciar sem migrations."
    echo "Para aplicar migrations novas, desbloqueie a aplicação e rode:"
    echo "  docker compose exec app python manage.py migrate"
fi
exec python manage.py runsecure 0.0.0.0:8000
