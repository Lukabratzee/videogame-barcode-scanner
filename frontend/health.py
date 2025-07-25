import streamlit as st
import requests
import os
import time
import json

# Health check for Streamlit frontend
# This file serves as a health endpoint for Docker/Portainer monitoring

def health_check():
    """Simple health check for Streamlit frontend"""
    try:
        # Check backend connectivity
        backend_host = os.getenv("BACKEND_HOST", "localhost")
        backend_port = os.getenv("BACKEND_PORT", "5001")
        backend_url = f"http://{backend_host}:{backend_port}"
        
        # Test backend connection
        response = requests.get(f"{backend_url}/health", timeout=5)
        backend_healthy = response.status_code == 200
        
        health_data = {
            "status": "healthy" if backend_healthy else "degraded",
            "backend_connection": "connected" if backend_healthy else "disconnected",
            "timestamp": time.time(),
            "frontend": "streamlit",
            "backend_url": backend_url
        }
        
        return health_data
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
            "frontend": "streamlit"
        }

# Check if this is being accessed via health endpoint
if __name__ == "__main__":
    # For simple health checks, we can use this as a basic script
    health = health_check()
    print(json.dumps(health, indent=2))
