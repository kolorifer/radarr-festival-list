"""Launch/preflight without shell evaluation of the private environment file."""
import argparse
import os
from pathlib import Path
import re
import shlex
import sys


def read_environment(path):
    if path.stat().st_mode & 0o077:
        raise ValueError("Environment file must not be accessible to group/others (use chmod 600)")
    values = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"Invalid environment assignment on line {number}")
        fields = shlex.split(value, comments=False)
        if len(fields) > 1:
            raise ValueError(f"Quote values containing spaces on line {number}")
        values[name] = fields[0] if fields else ""
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path.home() / ".config/movie-intel/environment")
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    try:
        values = read_environment(args.env_file)
    except (OSError, ValueError):
        print("Cannot read private environment file; check its permissions and assignment syntax", file=sys.stderr)
        return 1
    os.environ.update(values)
    if not os.environ.get("MOVIE_INTEL_ACTION_STORE") or not os.environ.get("TMDB_CACHE_PATH"):
        state = Path.home() / ".local/state/movie-intel"
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not os.environ.get("MOVIE_INTEL_ACTION_STORE"):
            os.environ["MOVIE_INTEL_ACTION_STORE"] = str(state / "actions.json")
        if not os.environ.get("TMDB_CACHE_PATH"):
            os.environ["TMDB_CACHE_PATH"] = str(state / "tmdb-cache.json")
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    argv = [sys.executable, "-u", str(root / "movie_intel_service.py")]
    if args.check_config:
        argv.append("--check-config")
    os.execv(sys.executable, argv)


if __name__ == "__main__":
    sys.exit(main())
