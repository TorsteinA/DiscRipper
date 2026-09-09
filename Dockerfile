# Stage 1: Extract pre-compiled binaries from jlesage/makemkv
FROM jlesage/makemkv:latest AS makemkv_source

# Stage 2: Minimal runtime image
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LD_LIBRARY_PATH="/usr/lib:/opt/makemkv/lib"

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# Enable Debian contrib/non-free repos
RUN sed -i 's/Components: main/Components: main contrib non-free non-free-firmware/' /etc/apt/sources.list.d/debian.sources

# Install core runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    handbrake-cli \
    util-linux \
    eject \
    ffmpeg \
    curl \
    ca-certificates \
    libexpat1 \
    intel-media-va-driver-non-free \
    libva-drm2 \
    libva2 \
    va-driver-all \
    && rm -rf /var/lib/apt/lists/*

# Copy MakeMKV binaries and libraries directly from /opt/makemkv/
COPY --from=makemkv_source /opt/makemkv/bin/ /usr/bin/
COPY --from=makemkv_source /opt/makemkv/lib/ /opt/makemkv/lib/
COPY --from=makemkv_source /opt/makemkv/lib/ /usr/lib/

# Ensure binaries have explicit executable permissions
RUN chmod +x /usr/bin/makemkvcon /usr/bin/mmgplsrv*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]