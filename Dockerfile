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

# VOLUME ["data"] # décommenter pour persister data/ entre runs
# La cron est installée dynamiquement par entrypoint.sh depuis la variable CRON_SCHEDULE (défaut : 0 6 * * *)
CMD ["/app/entrypoint.sh"]
