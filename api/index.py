"""
Simplified Vercel serverless function for Jarvis Command Center
"""
import json
from pathlib import Path

# Simple handler that returns static JSON
def handler(request, response):
    """Main handler for Vercel serverless function"""

    # Get the request path
    path = request.get('path', '/')

    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }

    # Handle preflight requests
    if request.get('method') == 'OPTIONS':
        response.status = 200
        response.headers = headers
        response.body = ''
        return response

    # Load static resources data
    try:
        resources_path = Path(__file__).parent.parent / 'backend' / 'resources_data.json'
        if resources_path.exists():
            with open(resources_path, 'r') as f:
                resources_data = json.load(f)
        else:
            # Fallback data if file doesn't exist
            resources_data = {
                "skills": [],
                "agents": [],
                "workflows": [],
                "models": [],
                "scripts": []
            }
    except Exception as e:
        resources_data = {
            "skills": [],
            "agents": [],
            "workflows": [],
            "models": [],
            "scripts": [],
            "error": str(e)
        }

    # Route handling
    if path == '/api/health':
        response_data = {
            "status": "healthy",
            "service": "Jarvis Command Center",
            "version": "1.0.0"
        }
    elif path == '/api/resources/all':
        response_data = {
            "resources": resources_data,
            "counts": {
                "skills": len(resources_data.get("skills", [])),
                "agents": len(resources_data.get("agents", [])),
                "workflows": len(resources_data.get("workflows", [])),
                "models": len(resources_data.get("models", [])),
                "scripts": len(resources_data.get("scripts", [])),
                "total": sum(len(v) for k, v in resources_data.items() if k != "error" and isinstance(v, list))
            }
        }
    elif path == '/api/resources/skills':
        response_data = resources_data.get("skills", [])
    elif path == '/api/resources/agents':
        response_data = resources_data.get("agents", [])
    elif path == '/api/resources/workflows':
        response_data = resources_data.get("workflows", [])
    elif path == '/api/resources/models':
        response_data = resources_data.get("models", [])
    elif path == '/api/resources/scripts':
        response_data = resources_data.get("scripts", [])
    else:
        response_data = {
            "error": "Not found",
            "path": path,
            "message": "The requested endpoint was not found"
        }
        response.status = 404

    # Set response
    response.status = response.status or 200
    response.headers = headers
    response.body = json.dumps(response_data)

    return response