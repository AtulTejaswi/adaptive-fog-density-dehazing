#!/usr/bin/env bash
# Usage: ./save_progress.sh "commit message"
# Commits everything (respecting .gitignore) and pushes to GitHub.
set -e
MSG="${1:-progress update}"
cd "$(dirname "$0")"

if [ ! -d .git ]; then
  git init -b main
fi

# make sure heavy stuff never gets committed
if [ ! -f .gitignore ]; then
  cat > .gitignore <<'EOF'
data/
*.zip
*.tar*
__pycache__/
*.pyc
.venv/
.ipynb_checkpoints/
results/tmp/
.env
EOF
fi

git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit."
else
  git commit -m "$MSG"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git push -u origin "$(git branch --show-current)" || {
    echo "PUSH FAILED: check credentials / remote URL (git remote -v). Commit is saved locally."
    exit 1
  }
  git push --tags 2>/dev/null || true
  echo "Pushed to GitHub."
else
  echo "No remote set. Run: git remote add origin https://github.com/<user>/<repo>.git"
fi
