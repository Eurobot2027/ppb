#!/usr/bin/env python3
"""Restore namespaced ancestor branches from the archive; never merge or switch branches."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(*args):
    return subprocess.check_output(["git", "-c", "core.fsmonitor=false", *args], text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("docs/history"))
    parser.add_argument("--apply", action="store_true", help="Import objects and create missing refs")
    args = parser.parse_args()
    manifest = json.loads((args.archive / "refs.json").read_text())
    bundle = (args.archive / "ancestors.bundle").resolve()
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != manifest["bundle_sha256"]:
        raise ValueError("Bundle checksum mismatch")
    git("cat-file", "-e", manifest["baseline"] + "^{commit}")
    git("bundle", "verify", str(bundle))
    refs = {}
    for row in manifest["refs"]:
        if not row["archived_ref"]:
            continue
        source_ref = row["ref"]
        if source_ref.startswith("stash/"):
            dest = f"refs/legacy-stashes/{row['source']}/{source_ref.split('/')[-1]}"
        else:
            suffix = source_ref.removeprefix("refs/").removeprefix("remotes/")
            suffix = suffix.replace("heads/", "local/", 1)
            dest = f"refs/remotes/legacy-{row['source']}/{suffix}"
        existing = subprocess.run(["git", "show-ref", "--verify", "--hash", dest],
                                  text=True, capture_output=True)
        if existing.returncode == 0 and existing.stdout.strip() != row["commit"]:
            raise ValueError(f"Ref already exists with a different commit: {dest}")
        refs[dest] = row["commit"]
    if args.apply:
        git("fetch", "--no-tags", str(bundle), "refs/ancestors/*:refs/ancestors/*")
        for dest, sha in refs.items():
            # Supplying the expected old SHA makes concurrent ref changes fail.
            existing = subprocess.run(["git", "show-ref", "--verify", "--hash", dest],
                                      text=True, capture_output=True)
            old = existing.stdout.strip() if existing.returncode == 0 else "0" * 40
            git("update-ref", dest, sha, old)
    print(f"{'Restored' if args.apply else 'Would restore'} {len(refs)} ancestor branch/stash refs")


if __name__ == "__main__":
    main()
