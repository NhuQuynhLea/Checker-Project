#!/bin/bash

# Environment switcher script
# Usage: ./switch-env.sh local|railway

if [ "$1" = "local" ]; then
    echo "Switching to LOCAL environment..."
    if [ -f .env.local ]; then
        cp .env.local .env
        echo "✅ Switched to local development environment"
        echo "📝 Using: Docker PostgreSQL + Docker MinIO"
    else
        echo "❌ .env.local file not found!"
        exit 1
    fi
elif [ "$1" = "railway" ]; then
    echo "Switching to RAILWAY environment..."
    if [ -f .env.railway ]; then
        cp .env.railway .env
        echo "✅ Switched to Railway production environment"
        echo "📝 Using: Railway PostgreSQL + Railway MinIO"
    else
        echo "❌ .env.railway file not found!"
        exit 1
    fi
else
    echo "Usage: ./switch-env.sh [local|railway]"
    echo ""
    echo "Current environment configuration:"
    echo "DATABASE_HOST: $(grep DATABASE_HOST .env | cut -d'=' -f2)"
    echo "MINIO_ENDPOINT: $(grep MINIO_ENDPOINT .env | cut -d'=' -f2)"
    echo "MINIO_SECURE: $(grep MINIO_SECURE .env | cut -d'=' -f2)"
fi