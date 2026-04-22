# Stage 1: Build whisper.cpp
FROM ubuntu:22.04 AS build

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone https://github.com/ggerganov/whisper.cpp.git && \
    cd whisper.cpp && \
    cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF && \
    cmake --build build --config Release -j$(nproc)

# Stage 2: Runtime
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy whisper.cpp binary (statically linked, no shared libs needed)
COPY --from=build /build/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli

# Download large-v3 model (ggml format)
RUN mkdir -p /app/models && \
    curl -L -o /app/models/ggml-large-v3.bin \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin"

COPY transcribe.py /app/transcribe.py
COPY process.py /app/process.py
COPY requirements.txt /app/requirements.txt

RUN pip install uv && \
    uv pip install --system --no-cache -r /app/requirements.txt

WORKDIR /data

ENTRYPOINT ["python", "/app/transcribe.py"]
