FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

# tzdata so that TZ applies to SCHEDULE
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY kometka ./kometka

RUN useradd --uid 1000 --user-group --no-create-home kometka \
 && mkdir /data && chown kometka:kometka /data
USER kometka
VOLUME /data

ENTRYPOINT ["python", "-m", "kometka"]
