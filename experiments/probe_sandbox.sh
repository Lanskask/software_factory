#!/usr/bin/env bash
# Question: do `claude -p`, `git commit` and a Docker check run under `srt` and under `sbx` (clone mode)?
# Answer (srt 0.0.82, Claude Code on haiku, macOS + colima, 2026-11-12, cost under $0.01):
#   srt: claude -p                     yes, 10 s, with api.anthropic.com allowed and ~/.claude writable
#   srt: git commit in the repo        yes
#   srt: docker info                   no by default (the Docker unix socket is denied); yes with
#                                      network.allowUnixSockets = [<docker socket>]. That socket is root on the host,
#                                      so allowing it gives a Session the host's Docker: not a sandbox for Docker work
#   srt: write outside allowWrite      refused ("Operation not permitted")
#   sbx                                not run: it needs `brew install docker/tap/sbx`, a browser `sbx login` and a
#                                      Claude /login inside the sandbox, which only the Owner can do
# Usage: experiments/probe_sandbox.sh DIR   (DIR is an empty scratch directory; spends about $0.05 on haiku)
set -uo pipefail
cd "$1"
git init -q && git commit -q --allow-empty -m init
cat > srt-settings.json <<JSON
{"network": {"allowedDomains": ["api.anthropic.com", "statsig.anthropic.com", "sentry.io", "claude.ai"], "deniedDomains": []},
 "filesystem": {"denyRead": [], "allowWrite": [".", "$HOME/.claude", "$HOME/.claude.json", "/tmp", "$TMPDIR"], "denyWrite": []}}
JSON
t() { local s=$(date +%s) out rc; echo "== $1"; shift; out=$("$@" 2>&1); rc=$?; echo "$out" | tail -4; echo "exit=$rc seconds=$(( $(date +%s) - s ))"; }
p='Reply with exactly SANDBOX-OK-5521.'
if command -v srt >/dev/null; then
  S="srt --settings srt-settings.json"
  t "srt: claude -p" $S -c "claude -p '$p' --model haiku --max-budget-usd 0.05 --no-session-persistence"
  t "srt: git commit" $S -c "echo x > f.txt && git add f.txt && git commit -qm probe && git log --oneline -1"
  t "srt: docker info" $S -c "docker info --format '{{.ServerVersion}}'"
  sock=$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null | sed 's#^unix://##')
  python3 -c "import json,sys; s=json.load(open('srt-settings.json')); s['network']['allowUnixSockets']=[sys.argv[1]]; json.dump(s,open('srt-docker.json','w'))" "$sock"
  t "srt: docker info, socket allowed" srt --settings srt-docker.json -c "docker info --format '{{.ServerVersion}}'"
  t "srt: write outside allowWrite is refused" $S -c "touch $HOME/srt-probe-should-fail"
  rm -f "$HOME/srt-probe-should-fail"
else
  echo "srt not installed"
fi
if command -v sbx >/dev/null; then
  sbx policy init balanced >/dev/null 2>&1
  t "sbx: claude -p (clone)" sbx run --rm --clone claude . -- -p "$p" --model haiku --max-budget-usd 0.05
  t "sbx: git + docker (clone)" sbx run --rm --clone shell . -- -c "git commit -q --allow-empty -m probe && git log --oneline -1 && docker info --format '{{.ServerVersion}}'"
else
  echo "sbx not installed: brew trust docker/tap && brew install docker/tap/sbx && sbx login"
fi
