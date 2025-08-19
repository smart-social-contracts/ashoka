FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and fix broken packages
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --fix-broken
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    curl git python3 python3-pip python3-venv unzip sudo nano wget netcat net-tools openssh-server \
    ca-certificates \
    gnupg \
    lsb-release
RUN apt-get install -y --no-install-recommends postgresql postgresql-contrib

RUN apt-get clean

# --- Create persistent volumes ---
RUN mkdir -p /workspace/ollama
RUN mkdir -p /workspace/venv
RUN mkdir -p /workspace/chromadb_data


# --- SSH server ---
RUN mkdir -p ~/.ssh
RUN touch ~/.ssh/authorized_keys
RUN chmod 700 ~/.ssh
RUN chmod 600 ~/.ssh/authorized_keys
RUN mkdir -p /run/sshd

# --- Git configuration ---
RUN git config --global user.name "Docker User"
RUN git config --global user.email "docker@container.local"
RUN git config --global init.defaultBranch main
# Trust the workspace directory for Git operations
RUN git config --global --add safe.directory /app/ashoka

ARG DFX_VERSION=0.27.0
RUN DFX_VERSION=${DFX_VERSION} DFXVM_INIT_YES=true sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"
ENV PATH="/root/.local/share/dfx/bin:$PATH"

# --- Ollama installation ---
RUN curl -fsSL https://ollama.com/install.sh | sh
ENV PATH="/root/.ollama/bin:${PATH}"
ENV OLLAMA_HOME=/workspace/ollama

# --- PostgreSQL setup ---
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER ashoka_user WITH SUPERUSER PASSWORD 'ashoka_pass';" && \
    createdb -O ashoka_user ashoka_db
USER root

# --- Configure PostgreSQL for external connections ---
RUN sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/14/main/postgresql.conf
RUN echo 'host    all             all             0.0.0.0/0               scram-sha-256' >> /etc/postgresql/14/main/pg_hba.conf

# --- App environment ---
WORKDIR /app/ashoka

# Copy .git folder for repository operations
COPY .git .git

COPY tests tests
COPY run.sh run.sh
COPY start.sh start.sh
COPY start_or_restart_api.sh start_or_restart_api.sh
COPY pod_manager.py pod_manager.py
COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt
COPY api.py api.py
COPY dfx.json dfx.json
COPY realm_status_service.py realm_status_service.py
COPY realm_status_scheduler.py realm_status_scheduler.py
COPY REALM_STATUS_README.md REALM_STATUS_README.md
COPY prompts prompts
COPY database database
COPY test_runner.py test_runner.py
COPY test_runner.sh test_runner.sh
COPY scripts scripts

# Note: Python dependencies will be installed by run.sh into the persistent volume
# This prevents duplicate installations and allows for faster container restarts

# Ollama
EXPOSE 11434

# PostgreSQL
EXPOSE 5432

# ChromaDB
EXPOSE 8000

# SSH
EXPOSE 2222

# Flask (API)
EXPOSE 5000


CMD ["./start.sh"]
