#!/usr/bin/env python3
"""
Knowledge Base Indexing Script
Indexes all MD files across the system for fast search
"""

import sys
import os
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from knowledge_indexer import get_knowledge_indexer

def main():
    """Index all knowledge base files"""
    print("🚀 Starting Knowledge Base Indexing...")
    print("=" * 60)

    indexer = get_knowledge_indexer()

    # Define directories to index
    directories = [
        ("/Volumes/Extreme Pro/AI_WORKSPACE/SKILLS_LIBRARY", "**/*.md"),
        ("/Volumes/AI_WORKSPACE/SKILLS_LIBRARY", "**/*.md"),
        ("/Volumes/Extreme Pro/AI_WORKSPACE/CORE", "**/*.md"),
        ("/Volumes/AI_WORKSPACE/CORE", "**/*.md"),
        ("/Volumes/Extreme Pro/AI_WORKSPACE/SKILLS_LIBRARY/video_knowledge", "*.md"),
        ("/Volumes/AI_WORKSPACE/video_analyzer/analysis", "*.md"),
        ("/Volumes/Extreme Pro/AI_WORKSPACE/EXISTING_PROJECTS", "**/*.md"),
    ]

    total_stats = {
        'total': 0,
        'indexed': 0,
        'skipped': 0,
        'errors': 0,
        'duration': 0
    }

    for directory, pattern in directories:
        if os.path.exists(directory):
            print(f"\n📁 Indexing: {directory}")
            print(f"   Pattern: {pattern}")

            stats = indexer.index_directory(directory, pattern)

            # Aggregate statistics
            total_stats['total'] += stats['total']
            total_stats['indexed'] += stats['indexed']
            total_stats['skipped'] += stats['skipped']
            total_stats['errors'] += stats['errors']
            total_stats['duration'] += stats['duration']
        else:
            print(f"\n⚠️  Directory not found: {directory}")

    print("\n" + "=" * 60)
    print("📊 Indexing Complete!")
    print(f"   Total Files: {total_stats['total']:,}")
    print(f"   Newly Indexed: {total_stats['indexed']:,}")
    print(f"   Skipped (unchanged): {total_stats['skipped']:,}")
    print(f"   Errors: {total_stats['errors']:,}")
    print(f"   Total Time: {total_stats['duration']:.2f} seconds")

    # Get final statistics
    db_stats = indexer.get_stats()
    print(f"\n💾 Database Statistics:")
    print(f"   Total Documents: {db_stats['total_documents']:,}")
    print(f"   Database Size: {db_stats['database_size'] / 1024 / 1024:.2f} MB")
    print(f"   Categories: {', '.join(db_stats['categories'].keys())}")

    # Test search functionality
    print("\n🔍 Testing Search Functionality...")
    test_queries = ["agent", "skill", "workflow", "sacred circuits", "video"]

    for query in test_queries:
        results = indexer.search(query, limit=3)
        print(f"   '{query}': {len(results)} results found")

    print("\n✅ Knowledge base indexing complete and operational!")

if __name__ == "__main__":
    main()