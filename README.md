# Reddit Scout

AI-powered Reddit monitoring and engagement tool.

## Quick Start

```bash
# Start services
docker compose up

# Or run locally
uv pip install -e ".[dev]"
uvicorn reddit_scout.api.main:app --reload
```
