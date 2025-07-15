#!/bin/bash

# Controlla se deve essere eseguito in modalità cron
if [ "$ENABLE_CRON" = "true" ]; then
    echo "Starting in CRON mode..."
    
    # Configura il cron job
    CRON_SCHEDULE="${CRON_SCHEDULE:-*/5 * * * *}"  # Default: ogni 5 minuti
    
    # Crea uno script che passa tutte le variabili d'ambiente al cron job
    cat > /app/cron-wrapper.sh << EOF
#!/bin/bash
export SECURITY_GROUP_ID="${SECURITY_GROUP_ID}"
export PORT="${PORT:-22}"
export PROTOCOL="${PROTOCOL:-tcp}"
export RULE_DESCRIPTION="${RULE_DESCRIPTION:-Dynamic IP access}"
export FORCE_CHECK_HOURS="${FORCE_CHECK_HOURS:-24}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION}"
export PATH="/usr/local/bin:/usr/bin:/bin:\$PATH"

cd /app
/app/cron-job.sh
EOF

    chmod +x /app/cron-wrapper.sh
    
    # Crea il cron job che usa il wrapper
    echo "$CRON_SCHEDULE /app/cron-wrapper.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/sg-manager
    
    # Imposta i permessi
    chmod 0644 /etc/cron.d/sg-manager
    
    # Applica il cron job
    crontab /etc/cron.d/sg-manager
    
    # Crea il file di log
    touch /var/log/cron.log
    
    echo "Cron job configured: $CRON_SCHEDULE"
    echo "Starting cron daemon..."
    
    # Avvia cron in background
    cron
    
    # Esegue una prima volta immediatamente
    echo "Running initial check..."
    /app/cron-wrapper.sh
    
    # Monitora i log del cron
    tail -f /var/log/cron.log
else
    echo "Starting in SINGLE RUN mode..."
    # Esecuzione singola
    python /app/main.py
fi 