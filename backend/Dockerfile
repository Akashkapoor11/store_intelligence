FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# If a POS CSV is present in the build context, copy it into /data
# so the container's `SALES_CSV_PATH` (set to /data/...) can find it at runtime.
RUN mkdir -p /data \
	&& sh -c 'for f in /app/POS*; do [ -e "$f" ] && cp "$f" /data/ || true; done'

EXPOSE 8000

# Use shell form so $PORT env var is expanded at runtime (required for Render)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
