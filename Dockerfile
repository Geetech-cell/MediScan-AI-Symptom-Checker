# Dockerfile for MediScan API
# Builds a container that runs the FastAPI `main.py` app

FROM python:3.11-slim

# Set a working directory
WORKDIR /app

# Install system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create a models directory where user can mount model files
RUN mkdir -p /app/models

# Expose port (can be overridden by $PORT env var at runtime)
ENV PORT=8000
EXPOSE 8000

# Runtime: use uvicorn to serve the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
