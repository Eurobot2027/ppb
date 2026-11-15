# Recoverable ancestor history

This directory preserves ancestor development within PPB without merging an old
branch over newer code. The archive was created from local snapshots, without
changing the ancestor repositories or fetching their network remotes.

| Artifact | Purpose |
| --- | --- |
| [INVENTORY.md](INVENTORY.md) | Every local/cached remote branch and S7 stash, tip and ancestry status |
| [refs.json](refs.json) | Full hashes, source paths, missing commits, bundle checksum and intended archive refs |
| `ancestors.bundle` | Incremental Git pack for the 24 commits missing from PPB, with 18 missing-tip refs |
| `patches/` | Readable source diffs for missing commit snapshots, excluding generated output |

The bundle requires the original PPB history, recorded as baseline
`d34076c3f7e9021185f19c5a881da0dcc9c69c53`. It intentionally avoids duplicating
roughly 64 MB of history already present in this fork. **It is not a standalone
clone of either original repository** and cannot reconstruct the excluded CAD
branch. Use a normal full PPB clone, not a shallow checkout without prerequisites.

## Inspect and restore branch names

From the repository root:

```bash
git bundle verify docs/history/ancestors.bundle
git bundle list-heads docs/history/ancestors.bundle
python3 tools/restore_history.py
python3 tools/restore_history.py --apply
git branch -a
```

The first script invocation checks checksum/prerequisites/conflicts and previews;
`--apply` imports objects and restores namespaced refs without switching or
merging. It recreates already-merged source refs from existing PPB objects too.
Conflicting existing refs are rejected rather than overwritten.

- Source local branches appear as `legacy-s7/local/...` / `legacy-s8/local/...`.
- Source cached remote branches appear as `legacy-s7/origin/...` / `legacy-s8/origin/...`.
- S7 stashes appear under `refs/legacy-stashes/s7/0` through `/4`; they do not
  replace the current stash stack.
- Imported bundle refs also remain under `refs/ancestors/` for exact provenance.
- The source `origin/HEAD` aliases are recorded as ordinary snapshot refs here;
  no live link to an old GitHub remote is configured.

Examples after restoring:

```bash
git show legacy-s7/local/feature/path-follower
git diff refs/legacy-stashes/s7/0^1 refs/legacy-stashes/s7/0
git log --oneline HEAD..legacy-s7/local/feature/strategy-simulation
```

Do not bulk merge old branches into main. Read the [recovery decisions](../RECOVERY.md)
and port individual ideas against the new hardware. Publishing this recovery
commit will carry the archive/manifest; local refs alone are not pushed by a
normal `git push`.

To regenerate from the old directories, see [tools](../../tools/README.md).
