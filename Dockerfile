FROM python:3.12-slim

LABEL maintainer="Pierre Rossinès <pierre.rossines@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/RossinesP/git-ticker"
LABEL org.opencontainers.image.description="AI-powered git commit summarizer using LLM agents"

# Install git (required for repository operations)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry==1.8.2

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment (we're in a container)
RUN poetry config virtualenvs.create false

# Install dependencies (without dev dependencies)
RUN poetry install --no-interaction --no-ansi --only main

# Copy application code
COPY git_ticker/ ./git_ticker/
COPY validate_commits.py ./
COPY entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set git safe directory for GitHub Actions
RUN git config --global --add safe.directory '*'

ENTRYPOINT ["/app/entrypoint.sh"]

