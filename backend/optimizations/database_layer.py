"""
Database Layer for Jarvis Command Center V2
Provides persistence for tasks, metrics, and analytics
"""

import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path


class DatabaseManager:
    """Lightweight SQLite database manager with connection pooling"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(
                Path(__file__).parent.parent / 'data' / 'jarvis_data.db'
            )

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for performance
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")

        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            conn.executescript('''
                -- Tasks table
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent TEXT,
                    workflow TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata TEXT,  -- JSON
                    result TEXT     -- JSON
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
                CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent);

                -- Performance metrics table
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    response_time_ms INTEGER NOT NULL,
                    status_code INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    ip_address TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_endpoint ON metrics(endpoint);
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_metrics_status ON metrics(status_code);

                -- Sessions table
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    resources_loaded TEXT,  -- JSON
                    metrics TEXT            -- JSON
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);

                -- Cache statistics table
                CREATE TABLE IF NOT EXISTS cache_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT NOT NULL,
                    hits INTEGER DEFAULT 0,
                    misses INTEGER DEFAULT 0,
                    last_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_stats(cache_key);

                -- WebSocket connections table
                CREATE TABLE IF NOT EXISTS ws_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connection_id TEXT UNIQUE NOT NULL,
                    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    disconnected_at TIMESTAMP,
                    messages_sent INTEGER DEFAULT 0,
                    messages_received INTEGER DEFAULT 0,
                    total_bytes_sent INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_ws_connected ON ws_connections(connected_at DESC);
            ''')

    # ========== Task Management ==========

    def create_task(
        self,
        task_id: str,
        task_type: str,
        status: str = 'pending',
        **kwargs
    ) -> int:
        """Create new task"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO tasks (task_id, type, status, agent, workflow, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                task_type,
                status,
                kwargs.get('agent'),
                kwargs.get('workflow'),
                json.dumps(kwargs.get('metadata', {}))
            ))
            return cursor.lastrowid

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        result: Optional[Dict] = None
    ):
        """Update task status and result"""
        with self.get_connection() as conn:
            updates = ["updated_at = CURRENT_TIMESTAMP"]
            params = []

            if status:
                updates.append("status = ?")
                params.append(status)

                if status == 'completed':
                    updates.append("completed_at = CURRENT_TIMESTAMP")

            if result:
                updates.append("result = ?")
                params.append(json.dumps(result))

            params.append(task_id)

            conn.execute(f'''
                UPDATE tasks
                SET {", ".join(updates)}
                WHERE task_id = ?
            ''', params)

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM tasks WHERE task_id = ?',
                (task_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_recent_tasks(self, limit: int = 10) -> List[Dict]:
        """Get recent tasks"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_by_status(self, status: str, limit: int = 50) -> List[Dict]:
        """Get tasks by status"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (status, limit))
            return [dict(row) for row in cursor.fetchall()]

    # ========== Metrics Management ==========

    def log_metric(
        self,
        endpoint: str,
        method: str,
        response_time_ms: int,
        status_code: int,
        **kwargs
    ):
        """Log performance metric"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO metrics (
                    endpoint, method, response_time_ms, status_code,
                    user_agent, ip_address
                )
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                endpoint,
                method,
                response_time_ms,
                status_code,
                kwargs.get('user_agent'),
                kwargs.get('ip_address')
            ))

    def get_performance_stats(
        self,
        hours: int = 24,
        endpoint: Optional[str] = None
    ) -> List[Dict]:
        """Get performance statistics"""
        with self.get_connection() as conn:
            if endpoint:
                cursor = conn.execute('''
                    SELECT
                        endpoint,
                        method,
                        COUNT(*) as request_count,
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time,
                        PERCENTILE(response_time_ms, 0.95) as p95_response_time,
                        SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
                    FROM metrics
                    WHERE timestamp > datetime('now', '-' || ? || ' hours')
                        AND endpoint = ?
                    GROUP BY endpoint, method
                ''', (hours, endpoint))
            else:
                cursor = conn.execute('''
                    SELECT
                        endpoint,
                        COUNT(*) as request_count,
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time,
                        SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
                    FROM metrics
                    WHERE timestamp > datetime('now', '-' || ? || ' hours')
                    GROUP BY endpoint
                    ORDER BY request_count DESC
                ''', (hours,))

            return [dict(row) for row in cursor.fetchall()]

    def get_slowest_endpoints(self, limit: int = 10) -> List[Dict]:
        """Get slowest endpoints by average response time"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT
                    endpoint,
                    COUNT(*) as request_count,
                    AVG(response_time_ms) as avg_response_time,
                    MAX(response_time_ms) as max_response_time
                FROM metrics
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY endpoint
                HAVING request_count > 5
                ORDER BY avg_response_time DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # ========== Session Management ==========

    def create_session(self, session_id: str, resources: Dict):
        """Create new session"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO sessions (session_id, resources_loaded)
                VALUES (?, ?)
            ''', (session_id, json.dumps(resources)))

    def end_session(self, session_id: str, metrics: Dict):
        """End session with metrics"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE sessions
                SET ended_at = CURRENT_TIMESTAMP,
                    metrics = ?
                WHERE session_id = ?
            ''', (json.dumps(metrics), session_id))

    # ========== Cache Statistics ==========

    def record_cache_hit(self, cache_key: str):
        """Record cache hit"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO cache_stats (cache_key, hits, misses)
                VALUES (?, 1, 0)
                ON CONFLICT(cache_key) DO UPDATE SET
                    hits = hits + 1,
                    last_access = CURRENT_TIMESTAMP
            ''', (cache_key,))

    def record_cache_miss(self, cache_key: str):
        """Record cache miss"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO cache_stats (cache_key, hits, misses)
                VALUES (?, 0, 1)
                ON CONFLICT(cache_key) DO UPDATE SET
                    misses = misses + 1,
                    last_access = CURRENT_TIMESTAMP
            ''', (cache_key,))

    # ========== WebSocket Tracking ==========

    def record_ws_connection(self, connection_id: str):
        """Record WebSocket connection"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO ws_connections (connection_id)
                VALUES (?)
            ''', (connection_id,))

    def record_ws_disconnect(self, connection_id: str):
        """Record WebSocket disconnection"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE ws_connections
                SET disconnected_at = CURRENT_TIMESTAMP
                WHERE connection_id = ?
            ''', (connection_id,))

    def update_ws_stats(
        self,
        connection_id: str,
        messages_sent: int,
        bytes_sent: int
    ):
        """Update WebSocket statistics"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE ws_connections
                SET messages_sent = messages_sent + ?,
                    total_bytes_sent = total_bytes_sent + ?
                WHERE connection_id = ?
            ''', (messages_sent, bytes_sent, connection_id))

    # ========== Analytics ==========

    def get_system_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system analytics"""
        with self.get_connection() as conn:
            # Task statistics
            task_stats = conn.execute('''
                SELECT
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM tasks
                WHERE created_at > datetime('now', '-24 hours')
            ''').fetchone()

            # Performance statistics
            perf_stats = conn.execute('''
                SELECT
                    COUNT(*) as total_requests,
                    AVG(response_time_ms) as avg_response_time,
                    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
                FROM metrics
                WHERE timestamp > datetime('now', '-24 hours')
            ''').fetchone()

            # WebSocket statistics
            ws_stats = conn.execute('''
                SELECT
                    COUNT(*) as total_connections,
                    SUM(messages_sent) as total_messages,
                    SUM(total_bytes_sent) as total_bytes
                FROM ws_connections
                WHERE connected_at > datetime('now', '-24 hours')
            ''').fetchone()

            return {
                'tasks': dict(task_stats) if task_stats else {},
                'performance': dict(perf_stats) if perf_stats else {},
                'websockets': dict(ws_stats) if ws_stats else {},
                'generated_at': datetime.now().isoformat()
            }

    def cleanup_old_data(self, days: int = 30):
        """Clean up old data"""
        with self.get_connection() as conn:
            # Delete old completed tasks
            conn.execute('''
                DELETE FROM tasks
                WHERE status = 'completed'
                    AND completed_at < datetime('now', '-' || ? || ' days')
            ''', (days,))

            # Delete old metrics
            conn.execute('''
                DELETE FROM metrics
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            ''', (days,))

            # Delete old sessions
            conn.execute('''
                DELETE FROM sessions
                WHERE ended_at < datetime('now', '-' || ? || ' days')
            ''', (days,))
