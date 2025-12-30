# Security Deployment Guide - Jarvis Command Center V2

## Overview

This guide provides step-by-step instructions for deploying the secured version of Jarvis Command Center V2 with all security remediations implemented.

---

## Pre-Deployment Checklist

### Critical Security Items

- [ ] Change default admin password
- [ ] Generate secure JWT secret key
- [ ] Configure restrictive CORS origins
- [ ] Set up SSL/TLS certificates
- [ ] Configure environment variables
- [ ] Install security dependencies
- [ ] Run security scans
- [ ] Review audit logs configuration
- [ ] Test authentication flow
- [ ] Verify rate limiting

---

## Installation Steps

### 1. Install Dependencies

```bash
cd /Volumes/AI_WORKSPACE/CORE/jarvis_command_center/backend

# Install security requirements
pip install -r requirements_security.txt

# Verify installations
pip list | grep -E 'fastapi|passlib|jose|slowapi'
```

### 2. Generate Secure Credentials

```bash
# Generate JWT secret key
python3 -c "import secrets; print(f'JARVIS_SECRET_KEY={secrets.token_urlsafe(32)}')"

# Generate secure admin password
python3 -c "import secrets; print(f'Admin Password: {secrets.token_urlsafe(16)}')"
```

### 3. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit with secure values
nano .env
```

**Required Changes**:
- Set `JARVIS_SECRET_KEY` to generated value
- Update `ALLOWED_ORIGINS` to your production domains
- Configure `N8N_WEBHOOK_BASE` if using n8n
- Set `SSL_KEYFILE` and `SSL_CERTFILE` paths

### 4. Update Admin Password

Edit `backend/security_middleware.py`:

```python
# Line ~70
USERS_DB = {
    "admin": User("admin", pwd_context.hash("YOUR_SECURE_PASSWORD_HERE"), ["admin", "user"])
}
```

**OR** use environment-based configuration (recommended):

```python
import os
from pathlib import Path

# Load from secure file
ADMIN_PASSWORD = os.environ.get('JARVIS_ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    password_file = Path('/etc/jarvis/admin.secret')
    if password_file.exists():
        ADMIN_PASSWORD = password_file.read_text().strip()
    else:
        raise ValueError("Admin password not configured")

USERS_DB = {
    "admin": User("admin", pwd_context.hash(ADMIN_PASSWORD), ["admin", "user"])
}
```

### 5. SSL/TLS Certificate Setup

#### Option A: Self-Signed (Development Only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Move to secure location
sudo mkdir -p /etc/jarvis/ssl
sudo mv key.pem cert.pem /etc/jarvis/ssl/
sudo chmod 600 /etc/jarvis/ssl/key.pem
```

#### Option B: Let's Encrypt (Production)

```bash
# Install certbot
sudo apt install certbot  # Ubuntu/Debian
# OR
brew install certbot  # macOS

# Generate certificate
sudo certbot certonly --standalone -d jarvis.yourdomain.com

# Update .env with certificate paths
SSL_KEYFILE=/etc/letsencrypt/live/jarvis.yourdomain.com/privkey.pem
SSL_CERTFILE=/etc/letsencrypt/live/jarvis.yourdomain.com/fullchain.pem
```

### 6. CORS Configuration

Update `ALLOWED_ORIGINS` in `.env`:

```bash
# Development
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Production
ALLOWED_ORIGINS=https://jarvis.yourdomain.com,https://app.yourdomain.com
```

---

## Security Verification

### 1. Run Security Scans

```bash
# Static analysis with Bandit
bandit -r backend/ -f json -o security_scan.json

# Review results
cat security_scan.json | jq '.results[] | select(.issue_severity=="HIGH" or .issue_severity=="MEDIUM")'

# Dependency vulnerability check
safety check --json

# OR use pip-audit
pip-audit
```

### 2. Test Authentication

```bash
# Start server
python backend/secure_main_v2.py

# In another terminal, test authentication
curl -X POST http://localhost:8000/token \
  -F "username=admin" \
  -F "password=YOUR_PASSWORD"

# Should return JWT token
# {"access_token":"eyJ...", "token_type":"bearer", "expires_in":1800}
```

### 3. Verify Rate Limiting

```bash
# Test command rate limit (10/minute)
for i in {1..15}; do
  curl -X POST http://localhost:8000/command \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"command":"test"}' \
    -w "\nStatus: %{http_code}\n"
done

# Should return 429 (Too Many Requests) after 10 requests
```

### 4. Test CORS Protection

```bash
# Test from different origin (should be blocked)
curl -X GET http://localhost:8000/ \
  -H "Origin: http://evil.com" \
  -v

# Should not include Access-Control-Allow-Origin in response
```

### 5. Verify XSS Protection

```bash
# Test XSS payload (should be sanitized)
curl -X POST http://localhost:8000/command \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command":"<script>alert(1)</script>"}' \
  -w "\nStatus: %{http_code}\n"

# Should return 400 (Bad Request) or sanitized command
```

---

## Production Deployment

### 1. System Service Setup (Linux)

Create `/etc/systemd/system/jarvis.service`:

```ini
[Unit]
Description=Jarvis Command Center V2 (Secured)
After=network.target

[Service]
Type=simple
User=jarvis
Group=jarvis
WorkingDirectory=/opt/jarvis
Environment="PATH=/opt/jarvis/venv/bin"
EnvironmentFile=/etc/jarvis/.env
ExecStart=/opt/jarvis/venv/bin/python /opt/jarvis/backend/secure_main_v2.py
Restart=on-failure
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/jarvis

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable jarvis
sudo systemctl start jarvis
sudo systemctl status jarvis
```

### 2. Nginx Reverse Proxy (Recommended)

Create `/etc/nginx/sites-available/jarvis`:

```nginx
upstream jarvis_backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name jarvis.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/jarvis.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jarvis.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=jarvis_api:10m rate=60r/m;
    limit_req zone=jarvis_api burst=20 nodelay;

    # Proxy to backend
    location / {
        proxy_pass http://jarvis_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket upgrade
    location /ws {
        proxy_pass http://jarvis_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Disable docs in production
    location /docs {
        return 404;
    }

    location /redoc {
        return 404;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name jarvis.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/jarvis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Firewall Configuration

```bash
# Allow only HTTPS
sudo ufw allow 443/tcp
sudo ufw enable

# If using SSH
sudo ufw allow 22/tcp

# Block direct access to backend port
sudo ufw deny 8000/tcp
```

---

## Monitoring & Maintenance

### 1. Log Monitoring

```bash
# Watch security logs
tail -f /var/log/jarvis/security.log

# Monitor authentication attempts
grep "auth_attempt" /var/log/jarvis/security.log | jq 'select(.success==false)'

# Monitor suspicious activity
grep "suspicious_activity" /var/log/jarvis/security.log
```

### 2. Automated Security Updates

Create `/etc/cron.daily/jarvis-security`:

```bash
#!/bin/bash
cd /opt/jarvis
source venv/bin/activate

# Update dependencies
pip install --upgrade -r backend/requirements_security.txt

# Run security scans
safety check
bandit -r backend/ -f txt > /var/log/jarvis/security_scan_$(date +%Y%m%d).txt

# Restart service if updates applied
systemctl restart jarvis
```

Make executable:

```bash
sudo chmod +x /etc/cron.daily/jarvis-security
```

### 3. Health Monitoring

```bash
# Create health check script
cat > /opt/jarvis/health_check.sh << 'EOF'
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://localhost:8000/health)

if [ "$RESPONSE" != "200" ]; then
    echo "Health check failed: $RESPONSE"
    systemctl restart jarvis
    # Send alert (configure email/slack/etc)
fi
EOF

chmod +x /opt/jarvis/health_check.sh

# Add to crontab (every 5 minutes)
crontab -e
# Add line: */5 * * * * /opt/jarvis/health_check.sh
```

---

## Security Best Practices

### 1. Regular Updates

```bash
# Weekly dependency updates
pip install --upgrade -r requirements_security.txt

# Monthly security scans
safety check
bandit -r backend/
```

### 2. Access Control

- Use separate accounts for admin vs regular users
- Implement role-based access control (RBAC)
- Rotate JWT secret keys quarterly
- Review and audit user permissions monthly

### 3. Backup & Recovery

```bash
# Backup configuration
tar -czf jarvis_config_backup_$(date +%Y%m%d).tar.gz \
  /etc/jarvis/.env \
  /etc/jarvis/ssl/ \
  /opt/jarvis/backend/security_middleware.py

# Store securely offsite
```

### 4. Incident Response

1. Monitor logs for suspicious activity
2. Implement alerting for critical events
3. Have rollback plan ready
4. Document security incidents
5. Regular security training for team

---

## Troubleshooting

### Authentication Issues

```bash
# Check token generation
python3 -c "from security_middleware import create_access_token; print(create_access_token({'sub': 'admin'}))"

# Verify password hash
python3 -c "from security_middleware import verify_password, USERS_DB; print(verify_password('YOUR_PASSWORD', USERS_DB['admin'].hashed_password))"
```

### CORS Errors

- Verify `ALLOWED_ORIGINS` includes your frontend domain
- Check browser console for specific error messages
- Ensure protocol (http/https) matches

### Rate Limiting Issues

```bash
# Check current limits
grep "RATE_LIMIT" .env

# Temporarily disable for testing (NOT in production)
# Comment out @limiter.limit decorators
```

### WebSocket Connection Failures

- Verify WebSocket token is valid
- Check firewall allows WebSocket connections
- Ensure nginx WebSocket upgrade headers configured
- Test with: `wscat -c ws://localhost:8000/ws?token=YOUR_TOKEN`

---

## Security Contacts

**Internal Security Team**: security@yourcompany.com
**External Audit**: [Contact information]
**Emergency Response**: [24/7 contact]

---

## Compliance Documentation

### OWASP Top 10 Coverage

- [x] A01:2021 - Broken Access Control
- [x] A02:2021 - Cryptographic Failures
- [x] A03:2021 - Injection
- [x] A04:2021 - Insecure Design
- [x] A05:2021 - Security Misconfiguration
- [ ] A06:2021 - Vulnerable Components (Ongoing)
- [x] A07:2021 - Identification/Authentication Failures
- [x] A08:2021 - Software/Data Integrity Failures
- [x] A09:2021 - Security Logging Failures
- [x] A10:2021 - Server-Side Request Forgery

### Security Certifications

- ISO 27001: [Status]
- SOC 2: [Status]
- PCI DSS: [Status if applicable]

---

**Document Version**: 1.0
**Last Updated**: 2025-12-30
**Next Review**: 2026-01-30
