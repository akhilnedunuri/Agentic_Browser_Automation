# ---------- Base Image ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ---------- Install full Playwright dependencies ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ca-certificates \
    xvfb \
    xauth \ 
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libxkbcommon0 \
    libxcomposite1 \
    libxrandr2 \
    libxdamage1 \
    libxfixes3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libglib2.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# ---------- Install Python dependencies ----------
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Install Playwright browsers ----------
RUN pip install --no-cache-dir playwright && \
    python -m playwright install --with-deps chromium firefox webkit

# ---------- Copy app code ----------
COPY . .

EXPOSE 8000

# ---------- Run under xvfb ----------
CMD ["sh", "-c", "xvfb-run --auto-servernum --server-args=\"-screen 0 1920x1080x24\" uvicorn main:app --host 0.0.0.0 --port 8000"]
