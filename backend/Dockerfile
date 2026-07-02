FROM python:3.11-slim

WORKDIR /app

# Install system utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY . backend/

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000
ENV DATABASE_URL=sqlite:///./agentforge.db

CMD ["python", "-m", "backend.app.main"]
