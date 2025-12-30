"""
API Key Integration Module for Jarvis Command Center
Manages API keys from the wallet for various services
Now with secure encryption and key rotation
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from secure_api_manager import get_secure_api_manager

class APIKeyManager:
    """Secure API key management with encryption"""

    def __init__(self):
        # Use new secure manager
        self.secure_manager = get_secure_api_manager()

        # Fallback to old wallet if secure manager fails
        self.wallet_path = "/Volumes/Extreme Pro/AI_WORKSPACE/CORE/jarvis/config/api_keys_wallet.json"
        self.keys = {}

        # Try to load from secure storage first
        try:
            self.keys = self.secure_manager.keys
        except Exception as e:
            print(f"Warning: Falling back to legacy wallet: {e}")
            self.keys = self._load_wallet()

    def _load_wallet(self) -> Dict[str, Any]:
        """Load API keys from wallet file (legacy fallback)"""
        try:
            if os.path.exists(self.wallet_path):
                with open(self.wallet_path, 'r') as f:
                    data = json.load(f)
                    return data.get('api_keys', {})
        except Exception as e:
            print(f"Warning: Could not load API wallet: {e}")
        return {}

    def get_key(self, service: str) -> Optional[str]:
        """Get API key for a service (now decrypted)"""
        # Try secure manager first
        try:
            key = self.secure_manager.get_key(service)
            if key:
                return key
        except Exception as e:
            print(f"Secure key retrieval failed: {e}")

        # Fallback to legacy method
        if service in self.keys:
            return self.keys[service].get('key')
        return None

    def get_active_services(self) -> Dict[str, Dict]:
        """Get all active services with their details (no keys exposed)"""
        # Try secure manager first
        try:
            return self.secure_manager.get_active_services()
        except:
            # Fallback to legacy method
            active = {}
            for service, details in self.keys.items():
                if details.get('status') == 'active':
                    active[service] = {
                        'service': service,
                        'note': details.get('note', ''),
                        'last_verified': details.get('last_verified', 'Unknown'),
                        'models': details.get('models_available', [])
                    }
            return active

    def get_service_config(self, service: str) -> Dict[str, Any]:
        """Get full configuration for a service (no keys exposed)"""
        config = self.keys.get(service, {}).copy()
        # Remove sensitive data
        config.pop('key', None)
        config.pop('encrypted_key', None)
        return config

    def rotate_key(self, service: str, new_key: str) -> bool:
        """Rotate an API key"""
        try:
            return self.secure_manager.rotate_key(service, new_key)
        except Exception as e:
            print(f"Key rotation failed: {e}")
            return False

    def audit_security(self) -> Dict[str, Any]:
        """Run security audit"""
        try:
            return self.secure_manager.audit_security()
        except Exception as e:
            return {"error": str(e)}

# Available API Services from wallet
API_SERVICES = {
    "gemini": {
        "name": "Google Gemini",
        "description": "Gemini 2.5 Flash, Pro, and Computer Use models",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash-exp"],
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/"
    },
    "openai": {
        "name": "OpenAI GPT",
        "description": "GPT-4 and GPT-3.5 access for text generation",
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "endpoint": "https://api.openai.com/v1/"
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "description": "Claude 3 Opus, Sonnet, and Haiku models",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "endpoint": "https://api.anthropic.com/"
    },
    "replicate": {
        "name": "Replicate ML",
        "description": "Access to various ML models for image/video processing",
        "capabilities": ["image-upscaling", "video-generation", "stable-diffusion"],
        "endpoint": "https://api.replicate.com/v1/"
    },
    "elevenlabs": {
        "name": "ElevenLabs Voice",
        "description": "Text-to-speech and voice synthesis",
        "voice_id": "IzuE4cSiMB3AFM2gOtiE",
        "endpoint": "https://api.elevenlabs.io/v1/"
    }
}

# Automation integrations
AUTOMATIONS = {
    "sacred-circuits": {
        "name": "Sacred Circuits",
        "description": "300+ tool automation platform with Seven Pillars architecture",
        "pillars": ["MIND", "CREATE", "COMPOSE", "AUTOMATE", "BUSINESS", "CONNECT", "SYSTEM"],
        "tools_count": 300,
        "location": "/Volumes/AI_WORKSPACE/EXISTING_PROJECTS/SACRED_CIRCUITS/Sacred-Circuits-Master/"
    },
    "audiobook": {
        "name": "Audiobook UI",
        "description": "Audiobook generation and management interface",
        "port": 5005,
        "capabilities": ["tts", "chapter-management", "voice-selection"]
    },
    "video-analyzer": {
        "name": "Video Analysis Pipeline",
        "description": "Extract knowledge from any video content",
        "capabilities": ["transcription", "frame-extraction", "knowledge-generation"],
        "location": "/Volumes/AI_WORKSPACE/video_analyzer/"
    },
    "n8n-workflows": {
        "name": "n8n Automation",
        "description": "Workflow automation platform",
        "workflows": [
            "master-video-pipeline",
            "telegram-video-analyzer",
            "knowledge-extraction",
            "skill-generation"
        ]
    },
    "telegram-bot": {
        "name": "Telegram Integration",
        "description": "Mobile access via Telegram bot",
        "bot_username": "@Videosxrapebot",
        "chat_id": 425517287
    }
}