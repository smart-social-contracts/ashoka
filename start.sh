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

# Pull latest changes
git pull

./run.sh

sleep 99999999  # Run indefinitely