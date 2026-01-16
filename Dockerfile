FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock* ./

# Install Python dependencies
RUN uv pip install --system -e .

# Copy application code
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY scripts/ ./scripts/

# Make entrypoint executable
RUN chmod +x scripts/entrypoint.sh

ENV PYTHONPATH=/app/src

ENTRYPOINT ["scripts/entrypoint.sh"]
CMD ["uvicorn", "reddit_scout.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
