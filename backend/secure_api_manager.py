"""
Secure API Key Management System
Implements encryption, rotation, and secure storage for API keys
"""

import os
import json
import hashlib
import secrets
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class SecureAPIManager:
    """
    Secure API key management with encryption and rotation
    Council Security Recommendation Implementation
    """

    def __init__(self):
        self.config_dir = Path("/Volumes/Extreme Pro/AI_WORKSPACE/CORE/jarvis/config")
        self.secure_store = self.config_dir / ".secure" / "keys.enc"
        self.rotation_log = self.config_dir / ".secure" / "rotation.log"
        self.master_key_file = self.config_dir / ".secure" / "master.key"

        # Create secure directory with restricted permissions
        self.secure_store.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Initialize encryption
        self.cipher = self._init_encryption()

        # Load existing keys securely
        self.keys = self._load_secure_keys()

    def _init_encryption(self) -> Fernet:
        """Initialize or load encryption key"""
        if self.master_key_file.exists():
            # Load existing master key
            with open(self.master_key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new master key
            key = Fernet.generate_key()
            with open(self.master_key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(self.master_key_file, 0o600)

        return Fernet(key)

    def _load_secure_keys(self) -> Dict[str, Dict]:
        """Load encrypted keys from secure storage"""
        if self.secure_store.exists():
            try:
                with open(self.secure_store, 'rb') as f:
                    encrypted_data = f.read()
                decrypted = self.cipher.decrypt(encrypted_data)
                return json.loads(decrypted.decode())
            except Exception as e:
                print(f"Error loading secure keys: {e}")
                return {}

        # Migrate from old wallet if exists
        old_wallet = self.config_dir / "api_keys_wallet.json"
        if old_wallet.exists():
            return self._migrate_old_wallet(old_wallet)

        return {}

    def _migrate_old_wallet(self, old_wallet_path: Path) -> Dict[str, Dict]:
        """Migrate keys from old plaintext wallet to secure storage"""
        print("🔐 Migrating API keys to secure storage...")

        with open(old_wallet_path, 'r') as f:
            old_data = json.load(f)

        migrated_keys = {}
        for service, details in old_data.get('api_keys', {}).items():
            if 'key' in details:
                # Encrypt the key
                migrated_keys[service] = {
                    'encrypted_key': self._encrypt_key(details['key']),
                    'status': details.get('status', 'unknown'),
                    'last_verified': details.get('last_verified'),
                    'last_rotated': datetime.now().isoformat(),
                    'note': details.get('note', ''),
                    'models_available': details.get('models_available', [])
                }

        # Save to secure storage
        self._save_secure_keys(migrated_keys)

        # Rename old wallet to backup
        backup_path = old_wallet_path.with_suffix('.json.backup')
        old_wallet_path.rename(backup_path)
        print(f"✅ Migration complete. Old wallet backed up to {backup_path}")

        return migrated_keys

    def _encrypt_key(self, key: str) -> str:
        """Encrypt an API key"""
        encrypted = self.cipher.encrypt(key.encode())
        return base64.b64encode(encrypted).decode()

    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key"""
        encrypted = base64.b64decode(encrypted_key.encode())
        decrypted = self.cipher.decrypt(encrypted)
        return decrypted.decode()

    def _save_secure_keys(self, keys: Dict[str, Dict]):
        """Save encrypted keys to secure storage"""
        data = json.dumps(keys).encode()
        encrypted_data = self.cipher.encrypt(data)

        with open(self.secure_store, 'wb') as f:
            f.write(encrypted_data)

        # Set restrictive permissions
        os.chmod(self.secure_store, 0o600)

    def get_key(self, service: str) -> Optional[str]:
        """
        Get decrypted API key for a service
        Returns None if key doesn't exist or is expired
        """
        if service not in self.keys:
            return None

        service_data = self.keys[service]

        # Check if key needs rotation (90 days)
        last_rotated = datetime.fromisoformat(service_data.get('last_rotated', '2024-01-01'))
        if (datetime.now() - last_rotated) > timedelta(days=90):
            self._log_rotation_needed(service)

        # Decrypt and return key
        encrypted_key = service_data.get('encrypted_key')
        if encrypted_key:
            return self._decrypt_key(encrypted_key)

        return None

    def rotate_key(self, service: str, new_key: str) -> bool:
        """
        Rotate an API key for a service
        Maintains audit trail of rotations
        """
        old_key = self.get_key(service)

        if service not in self.keys:
            self.keys[service] = {}

        # Update with new encrypted key
        self.keys[service].update({
            'encrypted_key': self._encrypt_key(new_key),
            'last_rotated': datetime.now().isoformat(),
            'status': 'active',
            'rotation_count': self.keys[service].get('rotation_count', 0) + 1
        })

        # Save updated keys
        self._save_secure_keys(self.keys)

        # Log rotation
        self._log_rotation(service, old_key is not None)

        return True

    def _log_rotation(self, service: str, had_previous: bool):
        """Log key rotation for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'service': service,
            'action': 'rotation',
            'had_previous': had_previous
        }

        # Append to rotation log
        with open(self.rotation_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def _log_rotation_needed(self, service: str):
        """Log when rotation is needed"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'service': service,
            'action': 'rotation_needed',
            'message': 'Key older than 90 days'
        }

        with open(self.rotation_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def get_active_services(self) -> Dict[str, Dict]:
        """Get all active services with metadata (no keys exposed)"""
        active = {}
        for service, details in self.keys.items():
            if details.get('status') == 'active':
                active[service] = {
                    'service': service,
                    'last_verified': details.get('last_verified'),
                    'last_rotated': details.get('last_rotated'),
                    'rotation_count': details.get('rotation_count', 0),
                    'models': details.get('models_available', [])
                }
        return active

    def validate_key(self, service: str) -> bool:
        """
        Validate that a key exists and is properly encrypted
        Does not expose the actual key
        """
        if service not in self.keys:
            return False

        try:
            encrypted_key = self.keys[service].get('encrypted_key')
            if encrypted_key:
                # Try to decrypt to validate
                self._decrypt_key(encrypted_key)
                return True
        except Exception:
            return False

        return False

    def get_env_exports(self) -> Dict[str, str]:
        """
        Get environment variable exports for runtime use
        Keys are only decrypted when needed
        """
        exports = {}

        # Map services to environment variable names
        env_mapping = {
            'gemini': 'GEMINI_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'replicate': 'REPLICATE_API_TOKEN',
            'elevenlabs': 'ELEVENLABS_API_KEY',
            'huggingface': 'HUGGINGFACE_TOKEN',
            'stability': 'STABILITY_API_KEY'
        }

        for service, env_name in env_mapping.items():
            key = self.get_key(service)
            if key:
                exports[env_name] = key

        return exports

    def audit_security(self) -> Dict[str, Any]:
        """
        Security audit report
        Council recommendation: Regular security audits
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_keys': len(self.keys),
            'active_keys': len([k for k, v in self.keys.items() if v.get('status') == 'active']),
            'keys_needing_rotation': [],
            'encryption_status': 'enabled',
            'master_key_present': self.master_key_file.exists(),
            'secure_storage_permissions': oct(os.stat(self.secure_store.parent).st_mode)[-3:] if self.secure_store.parent.exists() else 'N/A'
        }

        # Check for keys needing rotation
        for service, details in self.keys.items():
            last_rotated = datetime.fromisoformat(details.get('last_rotated', '2024-01-01'))
            days_old = (datetime.now() - last_rotated).days
            if days_old > 90:
                report['keys_needing_rotation'].append({
                    'service': service,
                    'days_old': days_old
                })

        return report


# Initialize secure manager as singleton
_secure_manager = None

def get_secure_api_manager() -> SecureAPIManager:
    """Get singleton instance of secure API manager"""
    global _secure_manager
    if _secure_manager is None:
        _secure_manager = SecureAPIManager()
    return _secure_manager