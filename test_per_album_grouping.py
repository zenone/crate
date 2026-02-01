#!/usr/bin/env python3
"""
Test script to verify per-album grouping logic.
Simulates the user's directory structure to debug why per-album banner isn't showing.
"""

import sys
import os
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from crate.core.context_detection import group_files_by_subdirectory, analyze_per_album_context

def test_grouping():
    """Test the grouping logic with user's directory structure."""

    # Simulate user's directory structure
    base_dir = "/Music/Parent"

    files = [
        {"path": f"{base_dir}/The Very Best of Fleetwood Mac/01 Fleetwood Mac - Go Your Own Way.mp3", "metadata": {"album": "The Very Best of Fleetwood Mac", "track": "1"}},
        {"path": f"{base_dir}/The Very Best of Fleetwood Mac/02 Fleetwood Mac - Dreams.mp3", "metadata": {"album": "The Very Best of Fleetwood Mac", "track": "2"}},
        {"path": f"{base_dir}/The Very Best of Fleetwood Mac/03 Fleetwood Mac - Little Lies.mp3", "metadata": {"album": "The Very Best of Fleetwood Mac", "track": "3"}},
        {"path": f"{base_dir}/The Very Best of Fleetwood Mac 2CD (2009)/Disc 1/01 Everywhere.mp3", "metadata": {"album": "The Very Best of Fleetwood Mac", "track": "1", "disc": "1"}},
        {"path": f"{base_dir}/The Very Best of Fleetwood Mac 2CD (2009)/Disc 1/02 Albatross.mp3", "metadata": {"album": "The Very Best of Fleetwood Mac", "track": "2", "disc": "1"}},
    ]

    print("=" * 80)
    print("TEST 1: Group files by subdirectory")
    print("=" * 80)

    album_groups = group_files_by_subdirectory(base_dir, files)

    print(f"\nBase directory: {base_dir}")
    print(f"Number of album groups: {len(album_groups)}")
    print(f"\nAlbum groups:")
    for album_key, group_files in album_groups.items():
        print(f"  - {album_key}: {len(group_files)} files")
        for f in group_files:
            print(f"      {Path(f['path']).name}")

    print("\n" + "=" * 80)
    print("TEST 2: Analyze per-album context")
    print("=" * 80)

    result = analyze_per_album_context(base_dir, files)

    print(f"\nPer-album mode: {result.get('per_album_mode')}")
    print(f"Number of albums: {len(result.get('albums', []))}")

    if result.get('per_album_mode'):
        print("\n✓ PER-ALBUM MODE ACTIVATED")
        print("\nAlbums detected:")
        for album in result.get('albums', []):
            print(f"  - Path: {album['path']}")
            print(f"    Album name: {album['album_name']}")
            print(f"    Files: {album['file_count']}")
            print(f"    Detection: {album['detection']['type']} ({album['detection']['confidence']})")
            print(f"    Template: {album['detection']['suggested_template']}")
            print(f"    Reason: {album['detection']['reason']}")
            print()
    else:
        print("\n✗ SINGLE-BANNER MODE (per-album mode NOT activated)")
        print(f"Reason: Less than 2 album groups detected")
        if result.get('global_suggestion'):
            print(f"Global suggestion: {result['global_suggestion']}")

    print("=" * 80)
    print("\nConclusion:")
    if len(album_groups) < 2:
        print("❌ ISSUE: Only found 1 album group (need 2+ for per-album mode)")
        print("   Possible causes:")
        print("   - All files might be in same subdirectory")
        print("   - Directory grouping logic might be incorrect")
    elif not result.get('per_album_mode'):
        print("❌ ISSUE: Found 2+ album groups but per_album_mode is False")
        print("   Possible causes:")
        print("   - Bug in analyze_per_album_context logic")
    else:
        print("✅ Working correctly - per-album mode should show in UI")
        print("   If UI still shows single-banner, check:")
        print("   - Feature flag enabled in settings")
        print("   - Browser console for errors")
        print("   - Network response in DevTools")
    print("=" * 80)

if __name__ == "__main__":
    test_grouping()
