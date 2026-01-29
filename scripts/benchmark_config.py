#!/usr/bin/env python3
"""
Benchmark script to demonstrate config caching performance improvement.

Compares performance of:
- Without cache: Forcing cache miss on every load (simulates old behavior)
- With cache: Normal cached loads (new behavior)

Run with: python scripts/benchmark_config.py
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dj_mp3_renamer.core.config import load_config, clear_config_cache


def benchmark_without_cache(iterations=1000):
    """
    Benchmark config loading without cache (simulate old behavior).

    Forces cache miss on every load by clearing cache between loads.
    """
    start = time.perf_counter()
    for _ in range(iterations):
        clear_config_cache()  # Force cache miss
        load_config()
    elapsed = time.perf_counter() - start
    return elapsed


def benchmark_with_cache(iterations=1000):
    """
    Benchmark config loading with cache (new behavior).

    First load is cache miss, subsequent loads are cache hits.
    """
    clear_config_cache()  # Start fresh
    start = time.perf_counter()
    for _ in range(iterations):
        load_config()  # Should hit cache after first load
    elapsed = time.perf_counter() - start
    return elapsed


def format_time(seconds):
    """Format time in ms with appropriate precision."""
    ms = seconds * 1000
    if ms < 1:
        return f"{ms * 1000:.1f}μs"
    else:
        return f"{ms:.2f}ms"


def main():
    """Run benchmarks and display results."""
    print("=" * 70)
    print("Config Caching Performance Benchmark")
    print("=" * 70)
    print()

    iterations = 1000
    print(f"Running {iterations} iterations for each benchmark...")
    print()

    # Benchmark without cache
    print("1. Without cache (forced cache miss every load)...")
    time_without_cache = benchmark_without_cache(iterations)
    print(f"   Total time: {format_time(time_without_cache)}")
    print(f"   Per load:   {format_time(time_without_cache / iterations)}")
    print()

    # Benchmark with cache
    print("2. With cache (cache hit after first load)...")
    time_with_cache = benchmark_with_cache(iterations)
    print(f"   Total time: {format_time(time_with_cache)}")
    print(f"   Per load:   {format_time(time_with_cache / iterations)}")
    print()

    # Calculate speedup
    speedup = time_without_cache / time_with_cache
    print("=" * 70)
    print(f"SPEEDUP: {speedup:.1f}x faster with caching")
    print("=" * 70)
    print()

    # Real-world impact
    print("Real-world impact:")
    print(f"  - 10 files:    Save ~{format_time((time_without_cache - time_with_cache) * 10 / iterations)}")
    print(f"  - 100 files:   Save ~{format_time((time_without_cache - time_with_cache) * 100 / iterations)}")
    print(f"  - 1000 files:  Save ~{format_time((time_without_cache - time_with_cache) * 1000 / iterations)}")
    print()


if __name__ == "__main__":
    main()
