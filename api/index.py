"""
Simplified Vercel serverless function for Jarvis Command Center
"""
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    """Main handler for Vercel serverless function"""

    def do_GET(self):
        """Handle GET requests"""
        self.handle_request()

    def do_POST(self):
        """Handle POST requests"""
        self.handle_request()

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def handle_request(self):
        """Process the actual request"""
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

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
        path = self.path

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

        # Write response
        self.wfile.write(json.dumps(response_data).encode('utf-8'))