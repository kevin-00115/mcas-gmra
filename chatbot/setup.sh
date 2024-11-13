#!/bin/bash

# Create necessary directories if they don't exist
mkdir -p documents
mkdir -p static
mkdir -p templates

# Set proper permissions
chmod 755 documents
chmod 755 static
chmod 755 templates

# Print current working directory and its permissions
pwd
ls -la

echo "Directory structure verified and fixed."