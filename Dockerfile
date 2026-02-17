# -------- Base image --------
FROM python:3.11-slim

# -------- Environment --------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------- Workdir --------
WORKDIR /app

# -------- System deps --------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# -------- Create non-root user --------
RUN useradd --create-home --shell /bin/bash appuser

# -------- Python deps --------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------- App code --------
COPY --chown=appuser:appuser app ./app

# -------- Switch to non-root user --------
USER appuser

# -------- Expose port --------
EXPOSE 8000

# -------- Start command --------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
