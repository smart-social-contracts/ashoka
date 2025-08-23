#!/bin/bash

ln -sf /usr/bin/python3 /usr/bin/python

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
    
    # Configure Git to use the SSH key
    git config --global core.sshCommand "ssh -i ~/.ssh/id_ed25519_docker_git -o IdentitiesOnly=yes"
    
    # Optional: Create SSH config for specific hosts
    cat > ~/.ssh/config << EOF
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_docker_git
    IdentitiesOnly yes

EOF
    chmod 600 ~/.ssh/config
fi

# Pull latest changes
git pull

./run.sh

sleep 99999999  # Run indefinitely