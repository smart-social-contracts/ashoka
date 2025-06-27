FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl git python3 python3-pip python3-venv unzip sudo nano wget netcat net-tools \
    && apt-get clean

RUN DFX_VERSION=0.27.0 DFXVM_INIT_YES=true sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"

# --- Ollama installation ---
RUN curl -fsSL https://ollama.com/install.sh | sh

# --- Add ollama to path ---
ENV PATH="/root/.ollama/bin:${PATH}"

# --- Set persistent home for Ollama ---
RUN mkdir -p /workspace/ollama
ENV OLLAMA_HOME=/workspace/ollama

WORKDIR /app
# --- Clone Ashoka repository ---
RUN git clone https://github.com/smart-social-contracts/ashoka.git

# --- Python environment ---
WORKDIR /app/ashoka

# Create initial directories that will be mirrored in the persistent volume
RUN mkdir -p /workspace/venv
RUN mkdir -p /workspace/chromadb_data

# Note: Python dependencies will be installed by run.sh into the persistent volume
# This prevents duplicate installations and allows for faster container restarts

EXPOSE 11434
EXPOSE 5000 8000

CMD ["./start.sh"]
