FROM nvidia/cuda:12.1.0-base-ubuntu20.04

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl git python3 python3-pip unzip sudo nano wget netcat net-tools \
    && apt-get clean

# --- Ollama installation ---
RUN curl -fsSL https://ollama.com/install.sh | sh

# --- Add ollama to path ---
ENV PATH="/root/.ollama/bin:${PATH}"

# --- Set persistent home for Ollama ---
RUN mkdir -p /workspace/ollama
ENV OLLAMA_HOME=/workspace/ollama

# We'll pull the model at runtime instead
# Models will be downloaded when container starts

# --- Python environment ---
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# --- Copy ashoka code ---
COPY cli/ /app/cli/
COPY tests/ /app/tests/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh


WORKDIR /app
EXPOSE 11434

CMD ["/app/start.sh"]
