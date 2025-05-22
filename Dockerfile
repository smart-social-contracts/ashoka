FROM nvidia/cuda:12.1.0-base-ubuntu20.04

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl git python3 python3-pip unzip sudo nano wget \
    && apt-get clean

# --- Ollama installation ---
RUN curl -fsSL https://ollama.com/install.sh | sh

# --- Add ollama to path + preload model ---
ENV PATH="/root/.ollama/bin:${PATH}"

# Pre-pull a model (optional)
RUN ollama pull llama3

# --- Python environment ---
COPY requirements.txt .
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

# --- Copy ashoka code ---
COPY ashoka/ /app/ashoka/
COPY start.sh /start.sh
RUN chmod +x /start.sh

WORKDIR /app/ashoka
CMD ["/start.sh"]
