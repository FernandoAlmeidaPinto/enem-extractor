FROM python:3.11-slim

WORKDIR /app

# Install minimal build tools (helps installing some Python packages)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt /app/
COPY src /app/src
COPY provas /app/provas
COPY README.md /app/

ENV PYTHONPATH=/app/src

# Install Python dependencies and the package itself
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir /app

CMD ["python", "-m", "enem_extractor.main"]
