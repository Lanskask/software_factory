# Sandbox command syntax: `sbx` and `srt`

Read on 2026-11-17 from the vendors' pages (links at the end). Nothing here was run by the Factory yet: every line is
documented behaviour, not measured behaviour, until `experiments/probe_sandbox.sh` (issue #26) records a result. It
replaces the "no `sbx` or `srt` command syntax is documented" gap in `docs/plan-local-stack-and-sandbox.md`.

## Which tool, in one table

| Question                      | `sbx` (Docker Sandboxes)                                  | `srt` (sandbox-runtime)                               |
| ----------------------------- | --------------------------------------------------------- | ----------------------------------------------------- |
| Isolation                     | microVM per sandbox, own kernel and Docker daemon         | macOS Seatbelt (`sandbox-exec`) or Linux `bubblewrap` |
| Cost                          | CLI and local compute free; needs a (free) Docker account | free, no account                                      |
| macOS                         | Sonoma 14+, Apple silicon                                 | any macOS with `ripgrep`                              |
| Run a Docker container inside | yes, private daemon                                       | no by default (Docker socket stays blocked)           |
| Headless `claude -p`          | documented (see below)                                    | not documented                                        |
| Fail-open option to refuse    | none documented                                           | none: `srt` has no "allow unsandboxed" key            |

## `sbx`

Install and sign in (the sign-in opens a browser; Docker Desktop is not needed):

```bash
brew trust docker/tap
brew install docker/tap/sbx
sbx login
```

Run Claude Code in a sandbox, interactive, then list and remove it:

```bash
cd ~/my-project
sbx run --name my-sandbox claude            # mounts the folder read-write at the same path
sbx run claude -- "explain this project"    # arguments after `--` go to claude
sbx ls
sbx stop my-sandbox
sbx rm my-sandbox
```

Headless, the form a Run would use. Clone mode gives the Session a private clone, and the host repo is mounted
read-only, so the Session cannot touch the host working tree:

```bash
sbx create --name ci-task --clone claude .
sbx exec ci-task -- claude --dangerously-skip-permissions -p "Review the code and commit your changes"
git fetch sandbox-ci-task                   # brings the commits back; remove the sandbox only after this
sbx rm --force ci-task
```

`sbx exec` returns the command's exit status (125 when the exec itself fails, 127 when the program is missing). Add
`--json` for structured output. Clone mode is fixed at creation and the folder must be a git repository.

Network policy and credentials:

```bash
sbx policy init balanced                    # non-interactive preset; the "Locked Down" spelling is unverified
sbx policy ls
sbx policy allow network registry.npmjs.org
sbx secret set anthropic                    # API key, injected by a host-side proxy; the VM never sees it
sbx secret set github --command 'gh auth token'
sbx settings set telemetry.disabled true
```

- With a Claude subscription, run `/login` inside the sandboxed Claude instead of storing an API key.
- `sbx run -e VAR` passes a plain variable that the VM can read: never use it for keys.
- Host `~/.claude` is not imported: only the project's own `.claude/` reaches the sandbox.
- The Balanced preset allows broad wildcards such as `*.googleapis.com`, so it is not a data-exfiltration barrier.

## `srt`

```bash
npm install -g @anthropic-ai/sandbox-runtime
brew install ripgrep                        # macOS needs only this; Linux also needs bubblewrap and socat
srt "curl anthropic.com"                    # run a command under the sandbox
srt --settings ./srt-settings.json make test
srt --debug curl https://example.com        # prints what was blocked
```

`~/.srt-settings.json` is the default settings file and `--settings` overrides it. With no file, nothing may use the
network and writes go only to default paths. A file that exists but is empty or invalid makes `srt` exit with an error.

```json
{
  "network": { "allowedDomains": ["github.com", "*.npmjs.org"], "deniedDomains": [] },
  "filesystem": {
    "denyRead": ["~/.ssh"],
    "allowWrite": [".", "/tmp"],
    "denyWrite": [".env"]
  }
}
```

- Reads are allowed everywhere unless denied (`allowRead` beats `denyRead`). Writes are denied everywhere unless allowed
  (`denyWrite` beats `allowWrite`). An empty `allowedDomains` means no network.
- There is no fail-open key. The settings that weaken it are `enableWeakerNestedSandbox`, `allowNestedUserNamespaces`,
  `enableWeakerNetworkIsolation`, `allowAppleEvents` and `allowAllUnixSockets`. A Factory `preflight` should refuse a
  settings file that sets any of them (this replaces the plan's "refuse when its settings allow unsandboxed commands").
- Claude Code's own built-in sandbox is separate and does fail open: `sandbox.failIfUnavailable` defaults to `false`.
- Limits: filtering is by hostname (a broad entry like `github.com` can leak data), a program that ignores proxy
  variables is not filtered, allowing `/var/run/docker.sock` hands over the host, and a hard link inside an allowed
  folder can write outside it.
- Not documented: how to run `claude -p` under `srt` (it needs `api.anthropic.com` in `allowedDomains`, and the macOS
  Keychain login may not be reachable: both unverified).

## What this changes in the plan

- Step 1 (the probe) is partly answered: `sbx exec NAME -- claude ... -p` is documented for clone mode. What the probe
  still has to measure is whether it works with the subscription login, how long startup takes, and whether `make test`
  can start a container inside the VM.
- Sessions in `sbx` run with `--dangerously-skip-permissions`: the VM is the boundary there, so the Factory's
  `--allowedTools` lists would be extra, not the lock.
- For `srt` the Factory would prefix the `claude` command with `srt --settings <file>`; for `sbx` it would replace the
  command with `sbx exec <name> -- claude ...` and fetch the branch back with `git fetch sandbox-<name>`.

## Sources

- <https://github.com/anthropics/sandbox-runtime> (formerly `anthropic-experimental/sandbox-runtime`) and
  <https://code.claude.com/docs/en/sandboxing>
- <https://docs.docker.com/ai/sandboxes/> and its `install`, `get-started`, `usage`, `security`, `faq` and
  `workflows/automation` pages. Not read: the `sbx` CLI reference and the local network-policy page.
