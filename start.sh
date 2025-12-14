#!/bin/bash

ln -sf /usr/bin/python3 /usr/bin/python

# --- Cloudflare Tunnel ---
# Decode credentials from base64 environment variables
# Generate with: base64 -w 0 <file> && echo
if [ ! -z "$CLOUDFLARED_CREDS_B64" ]; then
    echo "Setting up Cloudflare Tunnel credentials..."
    printf '%s' "$CLOUDFLARED_CREDS_B64" | base64 -d > /root/.cloudflared/credentials.json
    chmod 600 /root/.cloudflared/credentials.json
    
    # Decode origin certificate if provided
    if [ ! -z "$CLOUDFLARED_PEM_B64" ]; then
        echo "Setting up Cloudflare origin certificate..."
        printf '%s' "$CLOUDFLARED_PEM_B64" | base64 -d > /root/.cloudflared/cert.pem
        chmod 600 /root/.cloudflared/cert.pem
    fi
    
    echo "Starting Cloudflare Tunnel..."
    cloudflared tunnel --config /root/.cloudflared/config.yml run realms-runpod > /var/log/cloudflared.log 2>&1 &
    CLOUDFLARED_PID=$!
    echo "Cloudflare Tunnel started (PID: $CLOUDFLARED_PID)"
else
    echo "WARNING: CLOUDFLARED_CREDS_B64 not set. Skipping tunnel setup."
fi

# Setup SSH key from environment variable
if [ ! -z "$SSH_AUTH_KEY" ]; then
    echo "Setting up SSH key from environment variable..."
    echo "$SSH_AUTH_KEY" > /root/.ssh/id_rsa
    chmod 600 /root/.ssh/id_rsa
    
    # Start SSH agent and add key
    eval $(ssh-agent -s)
    ssh-add /root/.ssh/id_rsa
    
    # Add GitHub to known hosts
    ssh-keyscan -H github.com >> /root/.ssh/known_hosts 2>/dev/null
    ssh-keyscan -H gitlab.com >> /root/.ssh/known_hosts 2>/dev/null
fi

# Setup SSH keys from base64 encoded environment variables
# To generate the b64 encoding and recover them:
# base64 -w 0 ~/.ssh/id_ed25519_docker_git | base64 -d 
# base64 -w 0 ~/.ssh/id_ed25519_docker_git.pub | base64 -d 
if [ ! -z "$SSH_GIT_KEY_PRIVATE_B64" ]; then
    echo "Setting up SSH private key from base64 encoded environment variable..."
    printf '%s' "$SSH_GIT_KEY_PRIVATE_B64" | base64 -d > ~/.ssh/id_ed25519_docker_git
    chmod 600 ~/.ssh/id_ed25519_docker_git
    
    # Setup public key if provided
    if [ ! -z "$SSH_GIT_KEY_PUBLIC_B64" ]; then
        echo "Setting up SSH public key from base64 encoded environment variable..."
        printf '%s' "$SSH_GIT_KEY_PUBLIC_B64" | base64 -d > ~/.ssh/id_ed25519_docker_git.pub
        chmod 644 ~/.ssh/id_ed25519_docker_git.pub
    fi
    
    # Start SSH agent and add key (if not already started)
    if [ -z "$SSH_AGENT_PID" ]; then
        eval $(ssh-agent -s)
    fi
    ssh-add ~/.ssh/id_ed25519_docker_git
    
    # Add GitHub to known hosts (if not already added)
    if [ ! -f /root/.ssh/known_hosts ] || ! grep -q "github.com" /root/.ssh/known_hosts; then
        ssh-keyscan -H github.com >> /root/.ssh/known_hosts 2>/dev/null
    fi
    
    # Configure Git to automatically use SSH for GitHub URLs
    git config --global url."git@github.com:".insteadOf "https://github.com/"
    git config --global core.sshCommand "ssh -i ~/.ssh/id_ed25519_docker_git -o IdentitiesOnly=yes"
fi

# Pull latest changes
git pull

./run.sh

sleep 99999999  # Run indefinitely