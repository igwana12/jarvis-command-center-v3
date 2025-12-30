#!/usr/bin/env python3
"""
Optimized Resource Loader with Caching and Better Error Handling
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from threading import Lock
from dataclasses import dataclass, field
from pydantic import BaseModel, ValidationError, Field
import json
import logging

logger = logging.getLogger("jarvis.resources")

# ======================
# Configuration Models
# ======================

class ResourceConfig(BaseModel):
    """Configuration for resource paths"""
    skills_dir: Path = Field(default=Path('/Volumes/AI_WORKSPACE/SKILLS_LIBRARY'))
    commands_dir: Path = Field(default=Path('/Users/igwanapc/.claude/commands'))
    n8n_workflows_config: Path = Field(default=Path('/Volumes/AI_WORKSPACE/n8n_automation/workflows.json'))
    n8n_webhook_base: str = Field(default="http://localhost:5678/webhook")
    cache_ttl_seconds: int = Field(default=300)  # 5 minutes
    max_file_read_size: int = Field(default=1024)  # bytes

    class Config:
        env_prefix = "JARVIS_"

# ======================
# Data Models with Validation
# ======================

class AgentInfo(BaseModel):
    """Validated agent information"""
    name: str
    description: str
    category: Optional[str] = None
    capabilities: List[str] = []

class CommandInfo(BaseModel):
    """Validated command information"""
    name: str
    description: str
    type: str  # 'sc', 'command', 'skill'
    parameters: List[str] = []

class SkillInfo(BaseModel):
    """Validated skill information"""
    name: str
    path: str
    description: str = ""
    files: List[str] = []
    tags: List[str] = []

class MCPServerInfo(BaseModel):
    """Validated MCP server information"""
    id: str
    name: str
    description: str
    status: str = "available"  # available, offline, error
    capabilities: List[str] = []

class WorkflowInfo(BaseModel):
    """Validated workflow information"""
    id: str
    name: str
    description: str
    webhook_id: str
    parameters: List[str] = []
    enabled: bool = True

# ======================
# Cache System
# ======================

@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    data: Any
    loaded_at: datetime
    hits: int = 0
    misses: int = 0

class ResourceCache:
    """Thread-safe cache for resource data"""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get cached data if valid"""
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None

            entry = self.cache[key]
            age = datetime.now() - entry.loaded_at

            if age > self.ttl:
                # Cache expired
                del self.cache[key]
                self.stats["evictions"] += 1
                self.stats["misses"] += 1
                return None

            # Cache hit
            entry.hits += 1
            self.stats["hits"] += 1
            return entry.data

    def set(self, key: str, data: Any):
        """Store data in cache"""
        with self.lock:
            self.cache[key] = CacheEntry(
                data=data,
                loaded_at=datetime.now()
            )

    def invalidate(self, key: Optional[str] = None):
        """Invalidate cache entry or all entries"""
        with self.lock:
            if key:
                self.cache.pop(key, None)
            else:
                self.cache.clear()
            logger.info(f"Cache invalidated: {key or 'all'}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            hit_rate = 0.0
            total = self.stats["hits"] + self.stats["misses"]
            if total > 0:
                hit_rate = (self.stats["hits"] / total) * 100

            return {
                "entries": len(self.cache),
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "evictions": self.stats["evictions"],
                "hit_rate_percent": round(hit_rate, 2)
            }

# ======================
# Optimized Resource Loader
# ======================

class OptimizedResourceLoader:
    """Enhanced resource loader with caching and validation"""

    def __init__(self, config: Optional[ResourceConfig] = None):
        self.config = config or ResourceConfig()
        self.cache = ResourceCache(ttl_seconds=self.config.cache_ttl_seconds)

    def _cached_load(self, cache_key: str, loader_func: Callable) -> Any:
        """Load with cache check"""
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit: {cache_key}")
            return cached

        # Load fresh data
        logger.debug(f"Cache miss: {cache_key} - loading...")
        try:
            data = loader_func()
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Failed to load {cache_key}: {e}")
            return {}

    def load_agents(self) -> Dict[str, AgentInfo]:
        """Load SuperClaude agents with validation"""
        return self._cached_load("agents", self._load_agents_impl)

    def _load_agents_impl(self) -> Dict[str, AgentInfo]:
        """Implementation of agent loading"""
        agents = {}

        # Core agents from Task tool
        core_agents_data = {
            "general-purpose": {
                "description": "General-purpose agent for researching complex questions and multi-step tasks",
                "category": "general",
                "capabilities": ["research", "multi-step", "analysis"]
            },
            "python-expert": {
                "description": "Deliver production-ready Python code",
                "category": "development",
                "capabilities": ["python", "coding", "best-practices"]
            },
            "system-architect": {
                "description": "Design scalable system architecture",
                "category": "architecture",
                "capabilities": ["architecture", "design", "scalability"]
            },
            "security-engineer": {
                "description": "Identify security vulnerabilities",
                "category": "security",
                "capabilities": ["security", "audit", "penetration-testing"]
            },
            "frontend-architect": {
                "description": "Create accessible, performant user interfaces",
                "category": "frontend",
                "capabilities": ["ui", "ux", "accessibility", "performance"]
            },
            "backend-architect": {
                "description": "Design reliable backend systems",
                "category": "backend",
                "capabilities": ["api", "database", "reliability", "scalability"]
            },
            "performance-engineer": {
                "description": "Optimize system performance",
                "category": "optimization",
                "capabilities": ["performance", "profiling", "optimization"]
            },
            "devops-architect": {
                "description": "Automate infrastructure and deployment",
                "category": "devops",
                "capabilities": ["ci-cd", "infrastructure", "automation"]
            },
            "quality-engineer": {
                "description": "Ensure software quality through testing",
                "category": "quality",
                "capabilities": ["testing", "qa", "quality-assurance"]
            },
            "root-cause-analyst": {
                "description": "Investigate complex problems",
                "category": "debugging",
                "capabilities": ["debugging", "analysis", "problem-solving"]
            },
        }

        for name, data in core_agents_data.items():
            try:
                agents[name] = AgentInfo(
                    name=name,
                    description=data["description"],
                    category=data.get("category"),
                    capabilities=data.get("capabilities", [])
                )
            except ValidationError as e:
                logger.error(f"Invalid agent data for {name}: {e}")

        return agents

    def load_commands(self) -> Dict[str, CommandInfo]:
        """Load slash commands with validation"""
        return self._cached_load("commands", self._load_commands_impl)

    def _load_commands_impl(self) -> Dict[str, CommandInfo]:
        """Implementation of command loading"""
        commands = {}

        # Load from .claude/commands directory
        if self.config.commands_dir.exists():
            for cmd_file in self.config.commands_dir.glob('*.md'):
                try:
                    with open(cmd_file, 'r') as f:
                        content = f.read(self.config.max_file_read_size)

                    # Extract description
                    lines = content.split('\n')
                    desc = lines[0].strip('#').strip() if lines else "No description"

                    cmd_name = f"/{cmd_file.stem}"
                    commands[cmd_name] = CommandInfo(
                        name=cmd_file.stem,
                        description=desc,
                        type="command"
                    )
                except Exception as e:
                    logger.warning(f"Failed to load command {cmd_file}: {e}")

        # Add SC commands
        sc_commands_data = {
            "/sc:brainstorm": "Interactive requirements discovery",
            "/sc:test": "Execute tests with coverage analysis",
            "/sc:design": "Design system architecture",
            "/sc:implement": "Feature implementation",
            "/sc:analyze": "Comprehensive code analysis",
            "/sc:troubleshoot": "Diagnose and resolve issues",
        }

        for cmd, desc in sc_commands_data.items():
            try:
                commands[cmd] = CommandInfo(
                    name=cmd.split(':')[1],
                    description=desc,
                    type="sc"
                )
            except Exception as e:
                logger.error(f"Failed to create SC command {cmd}: {e}")

        return commands

    def load_skills(self) -> Dict[str, SkillInfo]:
        """Load skills with validation"""
        return self._cached_load("skills", self._load_skills_impl)

    def _load_skills_impl(self) -> Dict[str, SkillInfo]:
        """Implementation of skill loading"""
        skills = {}

        if not self.config.skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self.config.skills_dir}")
            return skills

        for skill_folder in self.config.skills_dir.iterdir():
            if not skill_folder.is_dir() or skill_folder.name.startswith('.'):
                continue

            try:
                description = ""
                # Try to read skill description
                for desc_file in ['README.md', 'skill.md', f'{skill_folder.name}.md']:
                    desc_path = skill_folder / desc_file
                    if desc_path.exists():
                        with open(desc_path, 'r') as f:
                            content = f.read(self.config.max_file_read_size)
                            description = content.split('\n')[0].strip('#').strip()
                        break

                # List files
                files = [
                    f.name for f in skill_folder.iterdir()
                    if f.is_file() and not f.name.startswith('.')
                ][:20]  # Limit to 20 files

                skills[skill_folder.name] = SkillInfo(
                    name=skill_folder.name,
                    path=str(skill_folder),
                    description=description,
                    files=files,
                    tags=skill_folder.name.split('-')
                )
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_folder.name}: {e}")

        return skills

    def load_mcp_servers(self) -> Dict[str, MCPServerInfo]:
        """Load MCP servers with validation"""
        return self._cached_load("mcp_servers", self._load_mcp_servers_impl)

    def _load_mcp_servers_impl(self) -> Dict[str, MCPServerInfo]:
        """Implementation of MCP server loading"""
        servers = {}

        mcp_data = {
            "sequential-thinking": {
                "name": "Sequential Thinking",
                "description": "Complex multi-step reasoning and hypothesis testing",
                "capabilities": ["reasoning", "analysis", "planning"]
            },
            "playwright": {
                "name": "Playwright",
                "description": "Browser automation and testing",
                "capabilities": ["browser", "testing", "automation"]
            },
            "magic": {
                "name": "Magic UI",
                "description": "UI component generation from 21st.dev",
                "capabilities": ["ui", "components", "frontend"]
            },
            "context7": {
                "name": "Context7",
                "description": "Documentation lookup and pattern guidance",
                "capabilities": ["documentation", "search", "patterns"]
            },
        }

        for server_id, data in mcp_data.items():
            try:
                servers[server_id] = MCPServerInfo(
                    id=server_id,
                    name=data["name"],
                    description=data["description"],
                    capabilities=data.get("capabilities", [])
                )
            except ValidationError as e:
                logger.error(f"Invalid MCP server data for {server_id}: {e}")

        return servers

    def load_workflows(self) -> Dict[str, WorkflowInfo]:
        """Load n8n workflows with validation"""
        return self._cached_load("workflows", self._load_workflows_impl)

    def _load_workflows_impl(self) -> Dict[str, WorkflowInfo]:
        """Implementation of workflow loading"""
        workflows = {}

        if self.config.n8n_workflows_config.exists():
            try:
                with open(self.config.n8n_workflows_config, 'r') as f:
                    raw_data = json.load(f)

                for wf_id, wf_data in raw_data.items():
                    try:
                        workflows[wf_id] = WorkflowInfo(
                            id=wf_id,
                            name=wf_data.get("name", wf_id),
                            description=wf_data.get("description", ""),
                            webhook_id=wf_data.get("webhook_id", wf_id),
                            parameters=wf_data.get("parameters", []),
                            enabled=wf_data.get("enabled", True)
                        )
                    except ValidationError as e:
                        logger.error(f"Invalid workflow data for {wf_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to load workflows config: {e}")

        # Add default workflows if none loaded
        if not workflows:
            default_workflows = {
                "master-pipeline": {
                    "name": "Master Pipeline",
                    "description": "Main orchestration workflow",
                    "webhook_id": "master-pipeline",
                    "parameters": ["task", "priority"]
                }
            }

            for wf_id, wf_data in default_workflows.items():
                workflows[wf_id] = WorkflowInfo(
                    id=wf_id,
                    name=wf_data["name"],
                    description=wf_data["description"],
                    webhook_id=wf_data["webhook_id"],
                    parameters=wf_data["parameters"]
                )

        return workflows

    def search(self, query: str) -> Dict[str, List[Dict]]:
        """Search across all resources efficiently"""
        query_lower = query.lower()
        results = {
            "agents": [],
            "commands": [],
            "skills": [],
            "mcp_servers": [],
            "workflows": []
        }

        # Search agents
        agents = self.load_agents()
        for name, agent in agents.items():
            if query_lower in name.lower() or query_lower in agent.description.lower():
                results["agents"].append({
                    "name": name,
                    "description": agent.description,
                    "category": agent.category,
                    "score": self._calculate_relevance(query_lower, name, agent.description)
                })

        # Search commands
        commands = self.load_commands()
        for cmd, info in commands.items():
            if query_lower in cmd.lower() or query_lower in info.description.lower():
                results["commands"].append({
                    "name": cmd,
                    "description": info.description,
                    "type": info.type,
                    "score": self._calculate_relevance(query_lower, cmd, info.description)
                })

        # Search skills
        skills = self.load_skills()
        for name, skill in skills.items():
            if query_lower in name.lower() or query_lower in skill.description.lower():
                results["skills"].append({
                    "name": name,
                    "description": skill.description,
                    "path": skill.path,
                    "score": self._calculate_relevance(query_lower, name, skill.description)
                })

        # Sort results by relevance score
        for category in results:
            results[category].sort(key=lambda x: x.get("score", 0), reverse=True)

        return results

    def _calculate_relevance(self, query: str, name: str, description: str) -> float:
        """Calculate relevance score for search results"""
        score = 0.0

        # Exact match in name (highest weight)
        if query == name.lower():
            score += 100.0
        # Partial match in name
        elif query in name.lower():
            score += 50.0

        # Match in description
        if query in description.lower():
            score += 25.0

        # Word boundary matches (better than substring)
        words = query.split()
        for word in words:
            if word in name.lower().split('-'):
                score += 10.0
            if word in description.lower().split():
                score += 5.0

        return score

    def invalidate_cache(self, resource_type: Optional[str] = None):
        """Invalidate cache for specific resource or all"""
        if resource_type:
            self.cache.invalidate(resource_type)
        else:
            self.cache.invalidate()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return self.cache.get_stats()
