# FavaGitSync

A Fava extension that syncs your beancount ledger with a git remote repository.

## Installation

See [Fava extensions documentation](https://fava.pythonanywhere.com/example-beancount-file/help/extensions)
for general information on how to install extensions.

1. Copy the files to where Fava can find them
2. Add `2010-01-01 custom "fava-extension" "fava_git_sync"` to your ledger file
3. Make sure your git repo is already configured with the correct credentials,
   current branch, and push strategy (`push.default`)

## Status Indicators

The extension adds a **sync** button to the Fava header with a colored status indicator:

| Indicator | Meaning |
|-----------|---------|
| 🟢 | Synchronized — local and remote are in sync |
| 🟡 | Local changes — uncommitted changes or local commits need pushing |
| 🔴 | Remote changes — the remote has commits you haven't pulled yet |
| ❌ | Error — communication or git failure |

The status is checked automatically every 30 seconds.

## Sync Behaviour

Clicking the **sync** button does the following:

1. If there are **uncommitted local changes** → auto-commits them (`git add -A` + `git commit`)
2. Pulls remote changes (`git pull --rebase`)
3. Pushes to remote (`git push`)

### Conflicts

If both local and remote have changes, the rebase may cause a git conflict.

When this happens:
1. Resolve the conflict in the Fava editor
2. Click **Save**
3. Click **sync** again to commit the resolution and push
4. Repeat until the indicator shows 🟢