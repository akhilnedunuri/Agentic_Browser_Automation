# --------- Base image with Python ----------
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# ---------------- Install system dependencies ----------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libgtk-3-0 \
    libgbm-dev \
    libasound2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# ---------------- Copy requirements and install Python deps ----------------
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ---------------- Install Playwright and browsers ----------------
RUN pip install --no-cache-dir playwright && \
    python -m playwright install --with-deps chromium firefox webkit

# ---------------- Copy application code ----------------
COPY . .

# Expose FastAPI port
EXPOSE 8000

# ---------------- Command to run app with Xvfb ----------------
CMD ["sh", "-c", "xvfb-run --server-args='-screen 0 1920x1080x24' uvicorn main:app --host 0.0.0.0 --port 8000"]
