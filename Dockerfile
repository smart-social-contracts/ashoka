FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# --- System setup ---
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and fix broken packages
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --fix-missing \
    curl git python3 python3-pip python3-venv unzip sudo nano wget netcat net-tools openssh-server \
    postgresql postgresql-contrib \
    apache2 \
    ca-certificates \
    gnupg \
    lsb-release

# Add pgAdmin repository and install pgAdmin
RUN curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list
RUN apt-get update
RUN apt-get install -y pgadmin4-web libapache2-mod-wsgi-py3

# Configure Apache for pgAdmin4
RUN a2enmod wsgi headers rewrite

RUN apt-get clean

# --- SSH server ---
RUN mkdir -p ~/.ssh
RUN touch ~/.ssh/authorized_keys
RUN chmod 700 ~/.ssh
RUN chmod 600 ~/.ssh/authorized_keys
RUN mkdir -p /run/sshd

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
WORKDIR /app/ashoka
RUN git fetch origin && git checkout devin/1753388604-ashoka-rag-integration

# --- PostgreSQL setup ---
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER ashoka_user WITH SUPERUSER PASSWORD 'ashoka_pass';" && \
    createdb -O ashoka_user ashoka_db
USER root

# --- Configure PostgreSQL for external connections ---
RUN sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/14/main/postgresql.conf
RUN echo 'host    all             all             0.0.0.0/0               scram-sha-256' >> /etc/postgresql/14/main/pg_hba.conf

# --- Python environment ---
WORKDIR /app/ashoka

# Create initial directories that will be mirrored in the persistent volume
RUN mkdir -p /workspace/venv
RUN mkdir -p /workspace/chromadb_data

# Note: Python dependencies will be installed by run.sh into the persistent volume
# This prevents duplicate installations and allows for faster container restarts

EXPOSE 11434
EXPOSE 5000
EXPOSE 8000
EXPOSE 2222
EXPOSE 80

CMD ["./start.sh"]
