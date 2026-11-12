#!/bin/sh
# Make a fresh eval run directory: the slugify-cli fixture as a git repo on `main` with a local bare `origin`, and a
# `gh` stand-in in RUN_DIR.bin (there is no pull request to open on a local origin).
# Usage: sh evals/new_run.sh RUN_DIR [MODEL]   then: PATH="RUN_DIR.bin:$PATH" factory run RUN_DIR
set -eu
run=${1:?usage: evals/new_run.sh RUN_DIR [MODEL]}
model=${2:-haiku}
here=$(cd "$(dirname "$0")" && pwd)
[ ! -e "$run" ] || { echo "new_run: $run already exists" >&2; exit 1; }
cp -R "$here/slugify-cli" "$run"
run=$(cd "$run" && pwd)
mkdir "$run/.factory" "$run.bin"
sed "s/^model = .*/model = \"$model\"/" "$here/slugify-cli.toml" > "$run/.factory/config.toml"
printf '#!/bin/sh\necho https://example.invalid/eval/pull/0\n' > "$run.bin/gh"
chmod +x "$run.bin/gh"
git init -q --bare "$run.origin.git"
cd "$run"
git init -q -b main
git add -A
git commit -q -m "slugify-cli eval fixture"
git remote add origin "$run.origin.git"
git push -q -u origin main
echo "new_run: $run ready ($model). Run: PATH=\"$run.bin:\$PATH\" factory run $run"
