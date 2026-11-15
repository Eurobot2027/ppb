# History tools

Run these standard-library Python tools from the repository root. They do not use
containers or contact network remotes.

## Recreate the audit archive

```bash
python3 tools/recover_history.py \
  --s7 /path/to/mam_eurobot_2026_T1 --s8 /path/to/jon-snowbot
```

Reads source refs/status-independent committed content and all stash reflog
entries. Fetches objects into a temporary bare repository, compares against PPB
HEAD, excludes the SolidWorks branch, and writes the incremental bundle,
inventory/manifest and source-only patches under `docs/history/`. Source
repositories and current refs/index/worktree are not changed. Existing archive
files are replaced, so use `--output /tmp/new-audit` to inspect a later snapshot
before intentionally replacing this historical audit.

## Restore namespaced refs here

```bash
python3 tools/restore_history.py
python3 tools/restore_history.py --apply
```

Default is a checksum/prerequisite/conflict check and preview. `--apply` imports
bundle objects and creates namespaced ancestor branch/stash refs; it never merges,
switches branches, replaces local branches or applies a stash. Conflicting refs
are rejected. Existing refs at the same SHA make it safe to run again.

See [archive usage](../docs/history/README.md) for ref names and commands. `.git`
write permissions are necessary only for `--apply`; the archive itself is a
normal portable project artifact.
