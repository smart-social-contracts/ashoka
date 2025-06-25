#!/bin/bash

ln -sf /usr/bin/python3 /usr/bin/python

# Pull latest changes
git pull

./run.sh
