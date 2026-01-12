FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system -e ".[dev]"

COPY src/ ./src/

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "reddit_scout.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
