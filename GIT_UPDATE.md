# Git update prompt on the Raspberry Pi

When you connect over SSH, `~/bin/git-update.sh` displays the current branch of
`~/Desktop/ppb` and asks:

```text
Stash changes and pull latest updates? [y/N]:
```

- **`y` or `Y`** saves local changes in a timestamped Git stash, including
  untracked files, then pulls the current branch from `origin`.
- **Enter or any other answer** cancels the update and opens your shell normally.

The pull uses `--ff-only`: it updates the branch only when no merge is needed.
If the branches have diverged or a Git command fails, the script stops and shows
the error. Your SSH session stays open.

**Stashed changes are not restored automatically**, even if the pull fails.
They remain available through `git stash list` in the repository and can be
restored with `git stash apply` using the appropriate stash entry.

The script is launched by `~/.bashrc` once per interactive SSH session. It skips
file transfers and noninteractive commands. It updates source files only; it
does not rebuild ROS packages or restart running nodes.
