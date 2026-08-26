FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 and others
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg2-binary SQLAlchemy slowapi beautifulsoup4 line-bot-sdk

# Copy app
COPY . .

# Ensure data directory exists
RUN mkdir -p data chroma_db social_listening/data

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
