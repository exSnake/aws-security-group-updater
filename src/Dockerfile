# Dockerfile
FROM python:3.11-slim

# Installa cron e dipendenze
RUN apt-get update && apt-get install -y \
    cron \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installa le dipendenze Python
RUN pip install boto3 requests

# Crea directory di lavoro
WORKDIR /app

# Copia i file necessari
COPY main.py /app/
COPY entrypoint.sh /app/
COPY cron-job.sh /app/

# Crea directory per i dati persistenti
RUN mkdir -p /data

# Rende eseguibili gli script
RUN chmod +x /app/main.py /app/entrypoint.sh /app/cron-job.sh

# Entrypoint script
CMD ["/app/entrypoint.sh"]
