#!/bin/bash

# --- Configuration ---
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/.venv"
GUNICORN_LOG_FILE="$PROJECT_DIR/gunicorn.log"
GUNICORN_PID_FILE="$PROJECT_DIR/gunicorn.pid"

# Gunicorn settings
GUNICORN_WORKERS=4 # Adjust based on your server's CPU cores (e.g., 2 * cores + 1)
GUNICORN_BIND="127.0.0.1:8000"
GUNICORN_APP="backend.main:app"

# Function to start the application
start() {
    echo "🚀 Starting Rebirth Game services..."

    # 1. Stop any running Gunicorn instance
    if [ -f $GUNICORN_PID_FILE ]; then
        echo "Stopping existing Gunicorn process..."
        kill $(cat $GUNICORN_PID_FILE)
        rm $GUNICORN_PID_FILE
    else
        # Fallback: find and kill by name
        pkill -f "gunicorn: master \[backend.main:app\]"
    fi

    # 2. Activate virtual environment and start Gunicorn
    echo "Starting Gunicorn in the background..."
    source "$VENV_DIR/bin/activate"
    gunicorn --workers $GUNICORN_WORKERS \
             --bind $GUNICORN_BIND \
             --log-level info \
             --log-file $GUNICORN_LOG_FILE \
             --pid $GUNICORN_PID_FILE \
             --daemon \
             $GUNICORN_APP
    deactivate
    
    sleep 2 # Give Gunicorn a moment to start

    # 3. Reload Nginx to ensure it's running with the latest config
    echo "Starting/Reloading Nginx..."
    sudo systemctl reload nginx
    if ! sudo systemctl is-active --quiet nginx; then
        sudo systemctl start nginx
    fi

    echo "✅ Application started successfully!"
    echo "Backend logs are available at: $GUNICORN_LOG_FILE"
}

# Function to stop the application
stop() {
    echo "🛑 Stopping Rebirth Game services..."

    # 1. Stop Gunicorn
    if [ -f $GUNICORN_PID_FILE ]; then
        echo "Stopping Gunicorn process..."
        kill $(cat $GUNICORN_PID_FILE)
        rm $GUNICORN_PID_FILE
    else
        echo "Gunicorn PID file not found. Trying to stop by process name..."
        pkill -f "gunicorn: master \[backend.main:app\]"
    fi

    # 2. Stop Nginx (optional, you might want to keep it running)
    # echo "Stopping Nginx..."
    # sudo systemctl stop nginx

    echo "✅ Application stopped."
}

# --- Script Main Logic ---
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        echo "🔄 Restarting application..."
        stop
        sleep 2
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac

exit 0
