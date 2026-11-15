#!/usr/bin/env python3
"""Archive local ancestor refs without changing any source repo or this repo's refs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def git(repo, *args, binary=False):
    return subprocess.check_output(
        ["git", "-c", "core.fsmonitor=false", "-C", str(repo), *args],
        text=not binary, stderr=subprocess.PIPE,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s7", type=Path, required=True)
    parser.add_argument("--s8", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/history"))
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    baseline = git(Path.cwd(), "rev-parse", "HEAD").strip()
    records = []
    with tempfile.TemporaryDirectory(prefix="ppb-history-") as directory:
        archive = Path(directory)
        git(archive, "init", "--bare")
        git(archive, "fetch", "--no-tags", str(Path.cwd()), f"{baseline}:refs/ppb/baseline")
        for label, source in [("s7", args.s7.resolve()), ("s8", args.s8.resolve())]:
            refs = [line.split() for line in git(
                source, "for-each-ref", "--format=%(refname) %(objectname)",
                "refs/heads", "refs/remotes",
            ).splitlines()]
            refs += [(f"stash/{i}", sha) for i, sha in enumerate(
                git(source, "stash", "list", "--format=%H").splitlines())]
            fetch_specs = []
            for ref, sha in refs:
                excluded = "adding-solidworks-design" in ref
                dest = f"refs/ancestors/{label}/{ref.removeprefix('refs/')}"
                records.append(dict(source=label, ref=ref, commit=sha,
                                    archived_ref=None if excluded else dest,
                                    disposition="excluded: obsolete CAD" if excluded else "archived"))
                if not excluded:
                    fetch_specs.append(f"{sha}:{dest}")
            git(archive, "fetch", "--no-tags", str(source), *fetch_specs)
        for row in records:
            if row["archived_ref"]:
                row["commits_not_in_ppb"] = int(git(
                    archive, "rev-list", "--count", f"{baseline}..{row['commit']}"))
                row["subject"] = git(archive, "show", "-s", "--format=%s", row["commit"]).strip()
        bundle = output / "ancestors.bundle"
        # PPB already owns the baseline history. Keep only missing objects (about
        # 0.6 MB here), rather than duplicating 64 MB of inherited binary assets.
        git(archive, "bundle", "create", str(bundle), "--all", "^" + baseline)
        git(archive, "bundle", "verify", str(bundle))
        # Each missing commit's source changes are reviewable without checking out an old tree.
        tips = [row["commit"] for row in records if row["archived_ref"]]
        commits = git(archive, "rev-list", "--reverse", *tips, "--not", baseline).splitlines()
        patch_dir = output / "patches"
        patch_dir.mkdir(exist_ok=True)
        filters = [".", ":(exclude)**/build/**", ":(exclude)**/install/**",
                   ":(exclude)**/log/**", ":(exclude)**/__pycache__/**",
                   ":(exclude)**/.DS_Store", ":(exclude)solidworks_designs/**"]
        for sha in commits:
            # Merge/stash snapshots are also captured relative to their first parent.
            patch = git(archive, "diff", "--binary", "--ignore-space-at-eol",
                        sha + "^1", sha, "--", *filters, binary=True)
            if patch:
                (patch_dir / f"{sha}.patch").write_bytes(patch)
        manifest = dict(baseline=baseline, bundle_requires_ppb_history=True,
                        sources={"s7": str(args.s7), "s8": str(args.s8)},
                        refs=records, missing_commits=commits,
                        bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest())
        (output / "refs.json").write_text(json.dumps(manifest, indent=2) + "\n")
        lines = ["# Local branch and stash inventory", "",
                 f"Compared with PPB `{baseline}`. No remote network fetch was performed.", "",
                 "`0` means the commit is already in PPB history; the branch name alone was lost.", "",
                 "| Source | Ref | Tip | Commits absent | Disposition |",
                 "| --- | --- | --- | ---: | --- |"]
        for row in records:
            lines.append(f"| {row['source']} | `{row['ref']}` | `{row['commit'][:12]}` | "
                         f"{row.get('commits_not_in_ppb', '—')} | {row['disposition']} |")
        lines += ["", f"{len(commits)} distinct commits absent from the baseline are preserved.", "",
                  "See [recovery decisions](../RECOVERY.md) and [archive usage](README.md).", ""]
        (output / "INVENTORY.md").write_text("\n".join(lines))
        print(f"Archived {len(records)} refs ({len(commits)} missing commits); bundle {bundle.stat().st_size} bytes")


if __name__ == "__main__":
    main()
