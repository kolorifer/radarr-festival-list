"""Store a repository-scoped GitHub token privately; never accept it in argv."""
import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from radarr_snapshot import CONFIG, GitHub, REPOSITORY
from radarr_movie_list_sync import write_private


def main():
    token = getpass.getpass("Fine-grained GitHub token for private radarr-state (hidden): ").strip()
    if not token or any(c.isspace() for c in token):
        print("Invalid credential", file=sys.stderr)
        return 1
    try:
        repo = GitHub(token).request("/repos/" + REPOSITORY)
        if repo.get("private") is not True or repo.get("full_name", "").casefold() != REPOSITORY.casefold():
            raise ValueError()
        destination = Path.home() / ".config/movie-intel/github-state-token"
        # write_private handles atomic replacement and 600; token file is plain text.
        CONFIG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        import os
        temporary = destination.with_name(destination.name + ".tmp")
        fd = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(token + "\n")
        temporary.replace(destination)
        write_private(CONFIG, {"repository": REPOSITORY})
    except Exception:
        print("Private GitHub access could not be verified; credential not configured", file=sys.stderr)
        return 1
    print("Private repository verified; publishing credential stored with mode600.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
