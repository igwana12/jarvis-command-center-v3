"""
Complete Resource API for Jarvis Command Center
Returns ALL discovered skills, agents, workflows, models, and scripts
"""

from fastapi import APIRouter
from typing import Dict, List, Any
import os
import json
import glob

router = APIRouter(prefix="/api/resources", tags=["resources"])

# Cache for discovered resources
_resource_cache = None

def load_static_resources() -> Dict[str, List[Dict[str, Any]]]:
    """Load resources from static JSON file for Vercel deployment"""
    import os
    from pathlib import Path

    # Try to load from JSON file
    json_path = Path(__file__).parent / "resources_data.json"
    if json_path.exists():
        with open(json_path, 'r') as f:
            return json.load(f)

    # Fallback to empty if file doesn't exist
    return {
        "skills": [],
        "agents": [],
        "workflows": [],
        "models": [],
        "scripts": []
    }

def discover_all_resources() -> Dict[str, List[Dict[str, Any]]]:
    """Discover ALL resources across the entire system"""

    resources = {
        "skills": [],
        "agents": [],
        "workflows": [],
        "models": [],
        "scripts": []
    }

    # SKILLS - All Python and specialized skill files
    skill_locations = [
        "/Volumes/AI_WORKSPACE/SKILLS_LIBRARY/*.py",
        "/Volumes/AI_WORKSPACE/video_analyzer/*.py",
        "/Volumes/AI_WORKSPACE/image_enhancer/*.py",
        "/Volumes/AI_WORKSPACE/bill_hicks_ai/*.py",
        "/Volumes/AI_WORKSPACE/n8n_automation/*.py",
        "/Volumes/AI_WORKSPACE/CORE/jarvis/modules/*.py",
        "/Volumes/AI_WORKSPACE/CORE/jarvis/skills/*.py",
        "/Volumes/Extreme Pro/AI_WORKSPACE/SKILLS_LIBRARY/*.py"
    ]

    skill_descriptions = {
        "video_analyzer": "Analyze videos from URLs, extract metadata, transcripts, and frames",
        "image_enhancer": "Enhance images using AI upscaling and quality improvement",
        "replicate_upscale": "Upscale images 4x using Replicate AI models",
        "bill_hicks_chat": "Interactive AI chat with Bill Hicks personality",
        "telegram_bridge": "Bridge for Telegram bot integration",
        "claude_bridge": "Integration with Claude AI API",
        "terminal_bridge": "Terminal command execution bridge",
        "youtube_downloader": "Download and process YouTube videos",
        "content_aggregator": "Aggregate content from multiple sources",
        "social_media_analyzer": "Analyze social media posts and trends",
        "text_summarizer": "Summarize long texts using AI",
        "code_reviewer": "Automated code review and suggestions",
        "data_visualizer": "Create visualizations from data",
        "web_scraper": "Extract data from websites",
        "api_tester": "Test and validate API endpoints",
        "database_manager": "Manage database operations",
        "file_organizer": "Organize files by type and date",
        "backup_manager": "Automated backup management",
        "security_scanner": "Scan for security vulnerabilities",
        "performance_monitor": "Monitor system performance",
        "log_analyzer": "Analyze and parse log files",
        "email_automation": "Automate email sending and processing",
        "calendar_integration": "Integrate with calendar services",
        "weather_fetcher": "Fetch weather data and forecasts",
        "news_aggregator": "Aggregate news from multiple sources",
        "stock_analyzer": "Analyze stock market data",
        "crypto_tracker": "Track cryptocurrency prices",
        "translation_service": "Translate text between languages",
        "voice_transcriber": "Transcribe audio to text",
        "pdf_processor": "Process and extract data from PDFs",
        "image_classifier": "Classify images using AI",
        "sentiment_analyzer": "Analyze sentiment in text",
        "keyword_extractor": "Extract keywords from documents",
        "document_converter": "Convert between document formats",
        "qr_code_generator": "Generate QR codes",
        "barcode_scanner": "Scan and decode barcodes",
        "color_palette_generator": "Generate color palettes from images",
        "font_identifier": "Identify fonts in images",
        "logo_detector": "Detect and extract logos",
        "face_recognition": "Recognize faces in images",
        "object_detection": "Detect objects in images",
        "text_to_speech": "Convert text to speech",
        "speech_to_text": "Convert speech to text",
        "music_analyzer": "Analyze music files",
        "audio_processor": "Process audio files",
        "video_editor": "Edit and process videos",
        "gif_creator": "Create animated GIFs",
        "meme_generator": "Generate memes with text",
        "screenshot_tool": "Capture screenshots",
        "screen_recorder": "Record screen activity",
        "clipboard_manager": "Manage clipboard history",
        "password_generator": "Generate secure passwords",
        "encryption_tool": "Encrypt and decrypt files",
        "hash_calculator": "Calculate file hashes",
        "network_scanner": "Scan network for devices",
        "port_scanner": "Scan ports on hosts",
        "dns_lookup": "Perform DNS lookups",
        "ip_locator": "Locate IP addresses geographically",
        "speed_test": "Test internet speed",
        "ping_monitor": "Monitor host availability",
        "traceroute_tool": "Trace network routes"
    }

    for pattern in skill_locations:
        for file_path in glob.glob(pattern):
            if not file_path.endswith('__pycache__'):
                name = os.path.basename(file_path).replace('.py', '')
                resources["skills"].append({
                    "name": name.replace('_', ' ').title(),
                    "title": name.replace('_', ' ').title(),
                    "description": skill_descriptions.get(name, f"Execute {name.replace('_', ' ')} operations"),
                    "path": file_path,
                    "type": "skill",
                    "category": os.path.dirname(file_path).split('/')[-1]
                })

    # AGENTS - All specialized AI agents
    agents_list = [
        {"name": "Python Expert", "description": "Expert Python development assistance with best practices"},
        {"name": "Security Engineer", "description": "Security auditing and vulnerability assessment"},
        {"name": "Frontend Architect", "description": "Frontend design and React/Vue/Angular expertise"},
        {"name": "Backend Architect", "description": "Backend system design and API architecture"},
        {"name": "Performance Engineer", "description": "Performance optimization and bottleneck analysis"},
        {"name": "Quality Engineer", "description": "Testing strategies and quality assurance"},
        {"name": "DevOps Architect", "description": "CI/CD pipelines and infrastructure automation"},
        {"name": "System Architect", "description": "System design and architecture patterns"},
        {"name": "Database Expert", "description": "Database design and optimization"},
        {"name": "Cloud Architect", "description": "Cloud infrastructure and deployment"},
        {"name": "Mobile Developer", "description": "iOS and Android app development"},
        {"name": "Data Scientist", "description": "Data analysis and machine learning"},
        {"name": "AI/ML Engineer", "description": "AI model development and deployment"},
        {"name": "Blockchain Developer", "description": "Blockchain and smart contract development"},
        {"name": "Game Developer", "description": "Game development and engine expertise"},
        {"name": "Embedded Systems Engineer", "description": "IoT and embedded systems programming"},
        {"name": "Network Engineer", "description": "Network architecture and protocols"},
        {"name": "UI/UX Designer", "description": "User interface and experience design"},
        {"name": "Technical Writer", "description": "Documentation and technical writing"},
        {"name": "Project Manager", "description": "Project planning and management"},
        {"name": "Business Analyst", "description": "Business requirements and analysis"},
        {"name": "Solution Architect", "description": "End-to-end solution design"}
    ]

    for agent in agents_list:
        resources["agents"].append({
            **agent,
            "title": agent["name"],
            "type": "agent",
            "category": "AI Agents"
        })

    # WORKFLOWS - All automation workflows
    workflow_locations = [
        "/Volumes/AI_WORKSPACE/n8n_automation/workflows/*.json",
        "/Volumes/AI_WORKSPACE/CORE/jarvis/workflows/*.json",
        "/Volumes/AI_WORKSPACE/workflows/*.json"
    ]

    workflow_descriptions = {
        "video_analysis": "Complete video analysis pipeline with transcript and frame extraction",
        "image_enhancement": "AI-powered image enhancement and upscaling workflow",
        "telegram_integration": "Telegram bot message processing and response",
        "content_pipeline": "Content processing and distribution pipeline",
        "data_processing": "Automated data processing workflow",
        "backup_automation": "Scheduled backup automation",
        "monitoring_workflow": "System monitoring and alerting",
        "deployment_pipeline": "Automated deployment pipeline",
        "testing_automation": "Automated testing workflow",
        "report_generation": "Automated report generation",
        "email_workflow": "Email processing and automation",
        "social_media_posting": "Scheduled social media posting",
        "web_scraping_pipeline": "Web scraping and data extraction",
        "file_processing": "Batch file processing workflow",
        "api_integration": "API integration workflow",
        "notification_system": "Multi-channel notification system",
        "sync_workflow": "Data synchronization workflow"
    }

    # Add predefined workflows
    for name, description in workflow_descriptions.items():
        resources["workflows"].append({
            "name": name.replace('_', ' ').title(),
            "title": name.replace('_', ' ').title(),
            "description": description,
            "type": "workflow",
            "category": "Automation"
        })

    # Check for actual workflow files
    for pattern in workflow_locations:
        for file_path in glob.glob(pattern):
            name = os.path.basename(file_path).replace('.json', '')
            if name not in workflow_descriptions:
                resources["workflows"].append({
                    "name": name.replace('_', ' ').title(),
                    "title": name.replace('_', ' ').title(),
                    "description": f"Workflow: {name.replace('_', ' ')}",
                    "path": file_path,
                    "type": "workflow",
                    "category": "Automation"
                })

    # MODELS - All AI models
    models_list = [
        {"name": "Claude 3 Opus", "description": "Most capable Claude model for complex tasks"},
        {"name": "Claude 3 Sonnet", "description": "Balanced performance and speed"},
        {"name": "Claude 3 Haiku", "description": "Fast responses for simple tasks"},
        {"name": "GPT-4 Turbo", "description": "OpenAI's most capable model"},
        {"name": "GPT-3.5 Turbo", "description": "Fast and cost-effective"},
        {"name": "DALL-E 3", "description": "Advanced image generation"},
        {"name": "Whisper", "description": "Speech recognition and transcription"},
        {"name": "Stable Diffusion XL", "description": "Open-source image generation"},
        {"name": "Llama 2 70B", "description": "Meta's large language model"},
        {"name": "Mistral 7B", "description": "Efficient open-source model"}
    ]

    for model in models_list:
        resources["models"].append({
            **model,
            "title": model["name"],
            "type": "model",
            "category": "AI Models"
        })

    # SCRIPTS - All executable scripts
    script_locations = [
        "/Volumes/AI_WORKSPACE/CORE/jarvis/scripts/*.sh",
        "/Volumes/AI_WORKSPACE/CORE/jarvis/scripts/*.py",
        "/Volumes/AI_WORKSPACE/scripts/*.sh",
        "/Volumes/AI_WORKSPACE/scripts/*.py",
        "/Volumes/AI_WORKSPACE/CORE/jarvis_command_center/*.sh",
        "/Volumes/AI_WORKSPACE/CORE/jarvis_command_center/scripts/*.sh",
        "/Volumes/AI_WORKSPACE/CORE/jarvis_command_center/scripts/*.py"
    ]

    script_descriptions = {
        "boot_jarvis": "Boot up the Jarvis system",
        "deploy_staging": "Deploy to staging environment",
        "deploy_production": "Deploy to production environment",
        "backup": "Run backup operations",
        "restore": "Restore from backup",
        "test_runner": "Run test suites",
        "performance_test": "Run performance tests",
        "security_scan": "Run security scans",
        "cleanup": "Clean temporary files",
        "monitor": "Monitor system status",
        "health_check": "System health check",
        "update_deps": "Update dependencies",
        "build": "Build the project",
        "start": "Start services",
        "stop": "Stop services",
        "restart": "Restart services",
        "logs": "View logs",
        "debug": "Debug mode",
        "install": "Install components",
        "configure": "Configure system",
        "migrate": "Run migrations",
        "seed": "Seed database",
        "export": "Export data",
        "import": "Import data",
        "sync": "Synchronize data",
        "validate": "Validate configuration",
        "optimize": "Optimize performance",
        "analyze": "Analyze system",
        "report": "Generate reports",
        "notify": "Send notifications",
        "schedule": "Schedule tasks",
        "queue": "Process queues"
    }

    for pattern in script_locations:
        for file_path in glob.glob(pattern):
            name = os.path.basename(file_path).replace('.sh', '').replace('.py', '')
            resources["scripts"].append({
                "name": name.replace('_', ' ').title(),
                "title": name.replace('_', ' ').title(),
                "description": script_descriptions.get(name, f"Execute {name.replace('_', ' ')} script"),
                "path": file_path,
                "type": "script",
                "category": "Scripts"
            })

    # Remove duplicates
    for resource_type in resources:
        seen = set()
        unique = []
        for item in resources[resource_type]:
            key = item.get('name', item.get('title'))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        resources[resource_type] = unique

    return resources

@router.get("/all")
async def get_all_resources():
    """Get ALL resources in the system"""
    global _resource_cache

    if not _resource_cache:
        # For Vercel deployment, use static JSON
        _resource_cache = load_static_resources()

    # Add counts
    response = {
        "resources": _resource_cache,
        "counts": {
            "skills": len(_resource_cache["skills"]),
            "agents": len(_resource_cache["agents"]),
            "workflows": len(_resource_cache["workflows"]),
            "models": len(_resource_cache["models"]),
            "scripts": len(_resource_cache["scripts"]),
            "total": sum(len(v) for v in _resource_cache.values())
        }
    }

    return response

@router.get("/skills")
async def get_skills():
    """Get all skills"""
    global _resource_cache
    if not _resource_cache:
        _resource_cache = load_static_resources()
    return _resource_cache["skills"]

@router.get("/agents")
async def get_agents():
    """Get all agents"""
    global _resource_cache
    if not _resource_cache:
        _resource_cache = load_static_resources()
    return _resource_cache["agents"]

@router.get("/workflows")
async def get_workflows():
    """Get all workflows"""
    global _resource_cache
    if not _resource_cache:
        _resource_cache = load_static_resources()
    return _resource_cache["workflows"]

@router.get("/models")
async def get_models():
    """Get all models"""
    global _resource_cache
    if not _resource_cache:
        _resource_cache = load_static_resources()
    return _resource_cache["models"]

@router.get("/scripts")
async def get_scripts():
    """Get all scripts"""
    global _resource_cache
    if not _resource_cache:
        _resource_cache = load_static_resources()
    return _resource_cache["scripts"]

@router.get("/refresh")
async def refresh_resources():
    """Refresh resource cache"""
    global _resource_cache
    _resource_cache = discover_all_resources()
    return {"status": "success", "message": "Resources refreshed"}