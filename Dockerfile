# Use the official uv image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# 1. Copy the dependency file
COPY pyproject.toml .

# 2. Install dependencies
RUN uv sync --no-dev --no-install-project

# 3. Copy the source code (according to your structure)
COPY agents/ agents/
COPY config/ config/
COPY core/ core/
COPY graph/ graph/
COPY tools/ tools/
COPY main.py .

# 4. Create directories for data and logs
RUN mkdir -p db data logs

# 5. Configure environment variables
ENV PATH="/app/.venv/bin:$PATH"
# Important: add current folder to PYTHONPATH so imports work correctly
ENV PYTHONPATH="/app"

# 6. Startup command
CMD ["python", "main.py", "start"]
