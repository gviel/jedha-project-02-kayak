FROM python:3.12-bookworm

# system deps required by Playwright/Chromium + cron
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron curl wget vim \
    libnss3 libgconf-2-4 \
    libgtk-3-0 libdbus-glib-1-2 libasound2 \
    libx11-xcb1 libxcomposite1 libxrandr2 libxss1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt && \
    playwright install --with-deps chromium

COPY . /app
WORKDIR /app

# arborescence data/ attendue par les scripts
RUN mkdir -p data/html data/csv data/json/cities data/json/weather

RUN chmod +x pipeline.sh entrypoint.sh

# cron : exécution du pipeline tous les jours à 06:00
RUN echo "0 6 * * * cd /app && /bin/bash /app/pipeline.sh >> /var/log/kayak.log 2>&1" | crontab -

# VOLUME ["data"] # décommenter pour persister data/ entre runs
CMD ["/app/entrypoint.sh"]
