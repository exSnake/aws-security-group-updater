#!/bin/bash

# Script per l'esecuzione del cron job
# Le variabili d'ambiente sono già impostate dal wrapper

echo "=== $(date) ==="
echo "Starting AWS Security Group Manager cron job..."

# Debug: mostra le variabili principali
echo "AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION}"
echo "AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}..." # Mostra solo i primi 10 caratteri
echo "SECURITY_GROUP_ID: ${SECURITY_GROUP_ID}"
echo "PORT: ${PORT}"
echo "PROTOCOL: ${PROTOCOL}"
echo "RULE_DESCRIPTION: ${RULE_DESCRIPTION}"
echo "---"

# Esegue lo script Python
cd /app
/usr/local/bin/python3 main.py

# Cattura il codice di uscita
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Cron job completed successfully"
else
    echo "Cron job failed with exit code: $exit_code"
fi

echo "=== End of cron job ==="
echo "" 