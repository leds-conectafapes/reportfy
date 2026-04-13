FROM python:3.11-slim

# System deps for matplotlib, networkx, and airbyte
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libffi-dev \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

# Configure matplotlib to use non-interactive backend
ENV MPLBACKEND=Agg

ENTRYPOINT ["python", "-m", "reportfy"]
