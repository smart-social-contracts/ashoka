FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl git python3 python3-pip unzip sudo nano wget netcat net-tools \
    && apt-get clean

RUN DFX_VERSION=0.27.0 DFXVM_INIT_YES=true sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"

# --- Ollama installation ---
RUN curl -fsSL https://ollama.com/install.sh | sh

# --- Add ollama to path ---
ENV PATH="/root/.ollama/bin:${PATH}"

# --- Set persistent home for Ollama ---
RUN mkdir -p /workspace/ollama
ENV OLLAMA_HOME=/workspace/ollama

# --- Clone Ashoka repository ---
RUN git clone https://github.com/smart-social-contracts/ashoka.git

# --- Python environment ---
WORKDIR /app/ashoka

EXPOSE 11434
EXPOSE 5000

CMD ["./start.sh"]
