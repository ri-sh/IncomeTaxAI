#!/usr/bin/env python3
"""
Manual cleanup script for immediate execution
"""

import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()

from api.cleanup_tasks import cleanup_dead_sessions, reset_stuck_documents, cleanup_old_task_results, validate_file_sessions

def main():
    print("🧹 Manual Cleanup Script")
    print("========================")
    print()
    
    # 1. Reset stuck documents (gentle approach)
    print("1. Resetting stuck documents...")
    try:
        result = reset_stuck_documents()
        print(f"   ✅ {result['message']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # 2. Clean up dead sessions (aggressive approach)
    print("2. Cleaning up dead sessions...")
    try:
        result = cleanup_dead_sessions()
        print(f"   ✅ {result['message']}")
        print(f"   📊 Stats: {result['stats']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # 3. Clean up old task results
    print("3. Cleaning up old task results...")
    try:
        result = cleanup_old_task_results()
        print(f"   ✅ Deleted {result.get('deleted_keys', 0)} old task results")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # 4. Validate file-session relationships
    print("4. Validating file-session relationships...")
    try:
        stats = validate_file_sessions()
        print(f"   📊 File validation stats:")
        print(f"      Total files: {stats['total_files']}")
        print(f"      Valid files: {stats['valid_files']}")
        print(f"      Orphaned files: {stats['orphaned_files']}")
        print(f"      Invalid session files: {stats['invalid_session_files']}")
        
        if stats['orphaned_files'] > 0 or stats['invalid_session_files'] > 0:
            print(f"   ⚠️  Found {stats['orphaned_files'] + stats['invalid_session_files']} problematic files")
        else:
            print("   ✅ All files have valid session relationships")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    print("✅ Manual cleanup completed!")
    print()
    print("💡 Automatic cleanup will run:")
    print("   - Every 10 minutes: Reset stuck documents")
    print("   - Every hour: Clean up dead sessions and validate files")
    print("   - Daily at 2 AM: Clean up old task results")

if __name__ == "__main__":
    main()