#!/usr/bin/env bash
set -euo pipefail

# Allowlist specific safe files (examples / the hook itself)
ALLOW_RE='^(configs/secrets/\.env\.example|scripts/secrets/forbid_dotenv_staged\.sh)$'

# Block top-level secrets dirs and sensitive filenames (not nested like scripts/secrets/)
PATTERN='(^|/)\.env($|\.|/)|^secrets/|^\.secrets/|(\.pem$)|(\.key$)|(id_rsa)|(id_ed25519)|(\.p12$)|(\.jks$)|(\.keystore$)'

mapfile -t STAGED < <(git diff --cached --name-only)

bad=()
for f in "${STAGED[@]}"; do
  [[ "$f" =~ $ALLOW_RE ]] && continue
  if [[ "$f" =~ $PATTERN ]]; then
    bad+=("$f")
  fi
done

if ((${#bad[@]})); then
  echo "[secrets] refusing to commit sensitive files:" >&2
  printf '%s\n' "${bad[@]}" >&2
  exit 1
fi
