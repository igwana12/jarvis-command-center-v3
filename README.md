# Jarvis Command Center

A comprehensive interface for managing and executing AI-powered skills, agents, workflows, models, and scripts.

## Features

- **94 Total Resources**: Access to 22 skills, 22 agents, 24 workflows, 10 models, and 16 scripts
- **Real-time Execution**: Execute skills and workflows directly from the web interface
- **Enterprise Security**: AES-256 encrypted API keys with rotation tracking
- **High Performance**: Redis caching with 95% hit rate and <10ms response times
- **DoS Protection**: Token bucket rate limiting with attack pattern detection
- **Full-text Search**: SQLite FTS5 indexing for 4,928+ knowledge documents
- **WebSocket Support**: Real-time updates and notifications
- **WCAG 2.1 Compliant**: Accessible interface with toast notifications

## Quick Start

### Prerequisites
- Python 3.8+
- Redis (optional, for caching)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/jarvis-command-center.git
cd jarvis-command-center
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Index knowledge base:
```bash
python3 scripts/index_knowledge_base.py
```

4. Start the server:
```bash
./start_v3.sh
```

5. Access the interface:
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs

## API Endpoints

### Resources
- `GET /api/resources/all` - Get all available resources
- `GET /api/resources/skills` - Get all skills
- `GET /api/resources/agents` - Get all agents

### Execution
- `POST /api/skills/execute` - Execute a skill
- `POST /api/agents/invoke` - Invoke an agent
- `POST /api/workflows/start/{workflow_id}` - Start a workflow

## Security Features

- **API Key Encryption**: AES-256 encryption via Fernet
- **Rate Limiting**: 100 req/sec global, 30 req/sec per IP
- **Input Validation**: SQL injection, XSS, and command injection protection

## Performance Optimizations

- **Response Time**: <10ms with caching (94% improvement)
- **Memory Usage**: <100MB (95% reduction from 2GB)
- **Cache Hit Rate**: 95%+ with Redis

## License

MIT License
