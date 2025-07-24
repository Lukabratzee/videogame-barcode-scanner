#!/bin/bash

echo "🔍 Docker Debug Script for Video Game Catalogue"
echo "================================================"

# Function to check if containers are running
check_containers() {
    echo "📋 Container Status:"
    docker-compose ps
    echo ""
}

# Function to show logs
show_logs() {
    echo "📝 Recent logs (last 50 lines):"
    echo "Backend logs:"
    echo "-------------"
    docker logs videogamescanner-backend --tail 50
    echo ""
    echo "Frontend logs:"
    echo "--------------"
    docker logs videogamescanner-frontend --tail 50
    echo ""
}

# Function to test browser automation inside container
test_browser() {
    echo "🌐 Testing browser automation inside backend container..."
    docker exec videogamescanner-backend /bin/bash -c "
        echo 'Testing Chrome installation...'
        google-chrome-stable --version
        echo 'Testing ChromeDriver...'
        /usr/local/bin/chromedriver --version
        echo 'Testing Xvfb display...'
        ps aux | grep Xvfb
        echo 'Testing Python dependencies...'
        python -c 'import undetected_chromedriver as uc; print(\"undetected-chromedriver imported successfully\")'
        python -c 'from selenium import webdriver; print(\"selenium imported successfully\")'
    "
}

# Function to enter backend container for debugging
enter_backend() {
    echo "🐚 Entering backend container shell..."
    docker exec -it videogamescanner-backend /bin/bash
}

# Function to enter frontend container for debugging
enter_frontend() {
    echo "🐚 Entering frontend container shell..."
    docker exec -it videogamescanner-frontend /bin/bash
}

# Main menu
case "${1:-menu}" in
    "status"|"s")
        check_containers
        ;;
    "logs"|"l")
        show_logs
        ;;
    "test"|"t")
        test_browser
        ;;
    "backend"|"b")
        enter_backend
        ;;
    "frontend"|"f")
        enter_frontend
        ;;
    "menu"|*)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  status, s    - Show container status"
        echo "  logs, l      - Show recent logs"
        echo "  test, t      - Test browser automation"
        echo "  backend, b   - Enter backend container shell"
        echo "  frontend, f  - Enter frontend container shell"
        echo ""
        echo "Examples:"
        echo "  $0 status"
        echo "  $0 logs"
        echo "  $0 test"
        echo "  $0 backend"
        ;;
esac 