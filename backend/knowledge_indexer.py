"""
Knowledge Base Indexer with SQLite
Efficiently indexes and searches 4,928+ MD files
Council Performance Recommendation Implementation
"""

import sqlite3
import hashlib
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import threading
import json

class KnowledgeIndexer:
    """
    SQLite-based indexing for MD files
    Handles 4,928+ files efficiently
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = "/Volumes/AI_WORKSPACE/CORE/jarvis_command_center/data/knowledge.db"

        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Thread-safe connection pool
        self.local = threading.local()

        # Initialize database
        self._init_database()

        # Index statistics
        self.stats = {
            'total_files': 0,
            'indexed_files': 0,
            'last_index': None,
            'index_time': 0
        }

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.conn.row_factory = sqlite3.Row
            # Enable optimizations
            self.local.conn.execute("PRAGMA journal_mode=WAL")
            self.local.conn.execute("PRAGMA synchronous=NORMAL")
            self.local.conn.execute("PRAGMA cache_size=10000")
            self.local.conn.execute("PRAGMA temp_store=MEMORY")
        return self.local.conn

    def _init_database(self):
        """Initialize database schema with indexes"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Main documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                category TEXT,
                title TEXT,
                content TEXT,
                summary TEXT,
                file_size INTEGER,
                modified_time REAL,
                indexed_time REAL,
                content_hash TEXT,
                metadata TEXT
            )
        """)

        # Full-text search table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
            USING fts5(
                file_path, title, content, summary,
                content=documents,
                content_rowid=id
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category
            ON documents(category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_name
            ON documents(file_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_modified
            ON documents(modified_time)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_hash
            ON documents(content_hash)
        """)

        # Tags table for categorization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id),
                PRIMARY KEY (document_id, tag_id)
            )
        """)

        # Statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_time REAL,
                total_files INTEGER,
                indexed_files INTEGER,
                duration_seconds REAL,
                errors INTEGER
            )
        """)

        conn.commit()

    def index_directory(self, directory: str, pattern: str = "**/*.md") -> Dict:
        """
        Index all MD files in directory
        Returns statistics about indexing operation
        """
        start_time = time.time()
        indexed = 0
        errors = 0
        skipped = 0

        conn = self._get_connection()
        cursor = conn.cursor()

        # Find all MD files
        path = Path(directory)
        files = list(path.glob(pattern))
        total_files = len(files)

        print(f"🔍 Indexing {total_files} files from {directory}...")

        for file_path in files:
            try:
                # Check if file needs reindexing
                stat = file_path.stat()
                content_hash = self._calculate_file_hash(file_path)

                # Check if already indexed and unchanged
                cursor.execute("""
                    SELECT content_hash FROM documents
                    WHERE file_path = ?
                """, (str(file_path),))

                existing = cursor.fetchone()
                if existing and existing['content_hash'] == content_hash:
                    skipped += 1
                    continue

                # Index the file
                self._index_file(file_path, cursor)
                indexed += 1

                # Progress update
                if indexed % 100 == 0:
                    print(f"   Indexed {indexed}/{total_files} files...")

            except Exception as e:
                print(f"   Error indexing {file_path}: {e}")
                errors += 1

        # Update FTS index
        cursor.execute("""
            INSERT INTO documents_fts(documents_fts)
            VALUES('rebuild')
        """)

        # Save statistics
        duration = time.time() - start_time
        cursor.execute("""
            INSERT INTO index_stats
            (index_time, total_files, indexed_files, duration_seconds, errors)
            VALUES (?, ?, ?, ?, ?)
        """, (time.time(), total_files, indexed, duration, errors))

        conn.commit()

        self.stats.update({
            'total_files': total_files,
            'indexed_files': indexed,
            'last_index': datetime.now().isoformat(),
            'index_time': duration
        })

        print(f"✅ Indexing complete: {indexed} new/updated, {skipped} unchanged, {errors} errors in {duration:.2f}s")

        return {
            'total': total_files,
            'indexed': indexed,
            'skipped': skipped,
            'errors': errors,
            'duration': duration
        }

    def _index_file(self, file_path: Path, cursor):
        """Index a single MD file"""
        # Read file content
        content = file_path.read_text(encoding='utf-8', errors='ignore')

        # Extract metadata
        title = self._extract_title(content)
        summary = self._generate_summary(content)
        category = self._categorize_file(file_path)
        tags = self._extract_tags(content)

        # File statistics
        stat = file_path.stat()
        content_hash = self._calculate_file_hash(file_path)

        # Prepare metadata JSON
        metadata = {
            'tags': tags,
            'lines': content.count('\n'),
            'words': len(content.split()),
            'headers': self._extract_headers(content)
        }

        # Upsert into database
        cursor.execute("""
            INSERT OR REPLACE INTO documents
            (file_path, file_name, category, title, content, summary,
             file_size, modified_time, indexed_time, content_hash, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(file_path),
            file_path.name,
            category,
            title,
            content,
            summary,
            stat.st_size,
            stat.st_mtime,
            time.time(),
            content_hash,
            json.dumps(metadata)
        ))

        # Update FTS index
        doc_id = cursor.lastrowid
        cursor.execute("""
            INSERT OR REPLACE INTO documents_fts
            (rowid, file_path, title, content, summary)
            VALUES (?, ?, ?, ?, ?)
        """, (doc_id, str(file_path), title, content, summary))

        # Handle tags
        for tag in tags:
            cursor.execute("""
                INSERT OR IGNORE INTO tags (tag_name) VALUES (?)
            """, (tag,))

            cursor.execute("""
                INSERT OR IGNORE INTO document_tags (document_id, tag_id)
                SELECT ?, id FROM tags WHERE tag_name = ?
            """, (doc_id, tag))

    def search(self, query: str, limit: int = 20, offset: int = 0) -> List[Dict]:
        """
        Search indexed documents using FTS5
        Returns list of matching documents with snippets
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Use FTS5 for full-text search
        cursor.execute("""
            SELECT
                d.id, d.file_path, d.file_name, d.title, d.category,
                d.file_size, d.modified_time,
                snippet(documents_fts, 2, '<mark>', '</mark>', '...', 30) as snippet,
                rank
            FROM documents_fts f
            JOIN documents d ON f.rowid = d.id
            WHERE documents_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        """, (query, limit, offset))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'file_path': row['file_path'],
                'file_name': row['file_name'],
                'title': row['title'],
                'category': row['category'],
                'snippet': row['snippet'],
                'file_size': row['file_size'],
                'modified': datetime.fromtimestamp(row['modified_time']).isoformat()
            })

        return results

    def get_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Get documents by category"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, file_path, file_name, title, summary, file_size
            FROM documents
            WHERE category = ?
            ORDER BY modified_time DESC
            LIMIT ?
        """, (category, limit))

        results = []
        for row in cursor.fetchall():
            results.append(dict(row))

        return results

    def get_categories(self) -> List[Dict]:
        """Get all categories with document counts"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM documents
            GROUP BY category
            ORDER BY count DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Get recently modified documents"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, file_path, file_name, title, category, modified_time
            FROM documents
            ORDER BY modified_time DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result['modified'] = datetime.fromtimestamp(row['modified_time']).isoformat()
            results.append(result)

        return results

    def get_stats(self) -> Dict:
        """Get indexing statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Document count
        cursor.execute("SELECT COUNT(*) as total FROM documents")
        total = cursor.fetchone()['total']

        # Category distribution
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM documents
            GROUP BY category
        """)
        categories = {row['category']: row['count'] for row in cursor.fetchall()}

        # Latest index run
        cursor.execute("""
            SELECT * FROM index_stats
            ORDER BY index_time DESC
            LIMIT 1
        """)
        latest = cursor.fetchone()

        return {
            'total_documents': total,
            'categories': categories,
            'latest_index': dict(latest) if latest else None,
            'database_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        }

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content"""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled"

    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate summary from content"""
        # Remove markdown formatting
        clean = re.sub(r'[#*`\[\]()]', '', content)
        # Get first paragraph
        paragraphs = clean.split('\n\n')
        for para in paragraphs:
            if len(para.strip()) > 20:
                summary = para.strip()[:max_length]
                if len(para) > max_length:
                    summary += '...'
                return summary
        return ""

    def _categorize_file(self, file_path: Path) -> str:
        """Categorize file based on path"""
        path_str = str(file_path).lower()

        if 'skill' in path_str:
            return 'skills'
        elif 'agent' in path_str:
            return 'agents'
        elif 'workflow' in path_str:
            return 'workflows'
        elif 'knowledge' in path_str or 'video_knowledge' in path_str:
            return 'knowledge'
        elif 'sacred' in path_str or 'circuit' in path_str:
            return 'sacred-circuits'
        elif 'council' in path_str:
            return 'council'
        elif 'doc' in path_str:
            return 'documentation'
        elif 'script' in path_str:
            return 'scripts'
        else:
            return 'general'

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content"""
        tags = []

        # Look for hashtags
        hashtags = re.findall(r'#(\w+)', content)
        tags.extend(hashtags[:10])  # Limit to 10 tags

        # Look for keywords in headers
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        for header in headers[:5]:
            words = header.lower().split()
            tags.extend([w for w in words if len(w) > 4][:2])

        return list(set(tags))[:15]  # Unique tags, max 15

    def _extract_headers(self, content: str) -> List[str]:
        """Extract markdown headers"""
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        return headers[:20]  # Limit to 20 headers

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file content hash for change detection"""
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()


# Singleton instance
_indexer = None

def get_knowledge_indexer() -> KnowledgeIndexer:
    """Get singleton instance of knowledge indexer"""
    global _indexer
    if _indexer is None:
        _indexer = KnowledgeIndexer()
    return _indexer