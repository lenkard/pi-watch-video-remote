FROM debian:bookworm-slim AS whisper-build
ARG WHISPER_CPP_REF=v1.7.2
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git build-essential cmake \
  && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${WHISPER_CPP_REF} https://github.com/ggerganov/whisper.cpp.git /src/whisper.cpp
WORKDIR /src/whisper.cpp
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_TESTS=OFF \
  && cmake --build build --config Release -j"$(nproc)"

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates ffmpeg libgomp1 \
  && rm -rf /var/lib/apt/lists/*
COPY --from=whisper-build /src/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli
COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY server/app /app/app
WORKDIR /app
ENV MODELS_DIR=/models DATA_DIR=/data WHISPER_CLI=/usr/local/bin/whisper-cli
VOLUME ["/models", "/data"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
