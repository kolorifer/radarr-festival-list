"""Read existing private credentials and run the separate Radarr sync CLI."""
import os
from pathlib import Path
import sys
from run import read_environment

def main():
    environment = Path.home() / ".config/movie-intel/environment"
    try:
        os.environ.update(read_environment(environment))
    except (OSError, ValueError):
        print("Cannot read private movie-intel environment", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    os.execv(sys.executable, [sys.executable, "-u", str(root / "radarr_movie_list_sync.py"), *sys.argv[1:]])

if __name__ == "__main__":
    sys.exit(main())
