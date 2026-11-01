"""
Main Command-Line Interface for the Scholarship Intelligence Platform.
Entry point for database initialization, URL discovery, crawling, change replay, and scheduling.
"""
import argparse
import sys
from database.db import initialize_database
from database.repository import ScholarshipRepository
from crawler.discovery import DiscoveryEngine
from crawler.pipeline import ScholarshipCrawlerPipeline
from crawler.scheduler import start_scheduler


def print_banner():
    banner = """
========================================================================
     EDXSO SCHOLARSHIP INTELLIGENCE & VERIFICATION PLATFORM
             Automated Primary Source Crawler & Audit Engine
========================================================================
    """
    print(banner)


def cmd_init_db(args):
    print_banner()
    print("[*] Initializing SQLite database and pre-populating trusted source registry...")
    initialize_database(recreate=args.recreate)
    repo = ScholarshipRepository()
    sources = repo.get_all_sources()
    print(f"[+] Database ready with {len(sources)} official source domains classified.")


def cmd_discover(args):
    print_banner()
    print("[*] Running multi-layer scholarship URL discovery...")
    discovery = DiscoveryEngine()
    counts = discovery.run_discovery(use_search=not args.no_search)
    print("\n[+] Discovery Completed:")
    for k, v in counts.items():
        print(f"    - {k}: {v}")


def cmd_crawl(args):
    print_banner()
    pipeline = ScholarshipCrawlerPipeline()
    res = pipeline.run_crawler(use_search=not args.no_search, verbose=True)
    return res


def cmd_test_changes(args):
    print_banner()
    print("[*] Running controlled change-detection test replay with versioned snapshots...")
    pipeline = ScholarshipCrawlerPipeline()
    res = pipeline.replay_change_test(verbose=True)
    print("[+] Change detection test completed successfully.")
    return res


def cmd_schedule(args):
    print_banner()
    interval = args.interval or 24
    print(f"[*] Starting background crawler schedule (interval: every {interval} hours)...")
    start_scheduler(interval_hours=interval)


def main():
    parser = argparse.ArgumentParser(
        description="EDXSO Scholarship Intelligence Crawler & Verification Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # init-db
    p_init = subparsers.add_parser("init-db", help="Initialize the SQLite database schema and sources")
    p_init.add_argument("--recreate", action="store_true", help="Drop and recreate database tables")

    # discover
    p_disc = subparsers.add_parser("discover", help="Discover candidate scholarship URLs")
    p_disc.add_argument("--no-search", action="store_true", help="Skip web search discovery")

    # crawl
    p_crawl = subparsers.add_parser("crawl", help="Run full crawl, extraction, verification, and storage pipeline")
    p_crawl.add_argument("--no-search", action="store_true", help="Skip search discovery during crawl")

    # test-changes
    p_test_ch = subparsers.add_parser("test-changes", help="Run controlled replay test demonstrating 2+ change detections")

    # schedule
    p_sched = subparsers.add_parser("schedule", help="Start automated periodic crawling scheduler")
    p_sched.add_argument("--interval", type=int, default=24, help="Crawl interval in hours (default: 24)")

    args = parser.parse_args()

    if args.command == "init-db":
        cmd_init_db(args)
    elif args.command == "discover":
        cmd_discover(args)
    elif args.command == "crawl":
        cmd_crawl(args)
    elif args.command == "test-changes":
        cmd_test_changes(args)
    elif args.command == "schedule":
        cmd_schedule(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
