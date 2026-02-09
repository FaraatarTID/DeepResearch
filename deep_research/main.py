import sys
import argparse
from .config import validate_config
from .search import purge_fetch_cache, cleanup_fetch_cache

def main():
    # Validate config
    valid, msg = validate_config()
    if not valid:
        print(f"Configuration Error: {msg}")
        print("Please create a .env file with the required keys.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Deep Research Tool")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (not implemented yet, defaults to GUI)")
    parser.add_argument("--purge-cache", action="store_true", help="Purge the fetch cache and exit")
    parser.add_argument("--cleanup-cache", action="store_true", help="Run cache cleanup and exit")
    args = parser.parse_args()
    
    if args.purge_cache:
        purge_fetch_cache()
        print("Cache purged.")
        return
    if args.cleanup_cache:
        cleanup_fetch_cache()
        print("Cache cleanup complete.")
        return

    if args.cli:
        print("CLI mode not fully implemented in this version. Launching GUI...")
        # TODO: Implement CLI runner
        
    from .gui import main as gui_main
    gui_main()

if __name__ == "__main__":
    main()
