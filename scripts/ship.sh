#!/usr/bin/env bash
#
# Deploy the glyph.fru.dev site (the static files in docs/: the Glyph family home and one page
# per app) to Vercel,
# team fru-dev3, project glyph-fru. No build step, no functions, no secrets.
#
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .vercel/project.json ] || vercel link --yes --project glyph-fru

# The app icons, copied from assets/family/ (git-ignored copies).
./scripts/sync-icons.sh

# The real stargazers, baked into every page (commit the result).
node scripts/fetch-stargazers.mjs || true

echo "building"
vercel build --prod --yes

# Deploys the prebuilt output from a copy outside the repo. Run inside it, the
# CLI attaches the git commit, and Vercel has blocked such deployments ("the
# commit author doesn't have permission") and left the CLI stuck at Building.
vdeploy() {
  local stage; stage=$(mktemp -d)
  mkdir "$stage/.vercel"
  cp -R .vercel/project.json .vercel/output "$stage/.vercel/"
  (cd "$stage" && vercel deploy "$@"); local rc=$?
  rm -rf "$stage"
  return $rc
}

echo "deploying"
vdeploy --prebuilt --prod

for p in / /studio /jot /rig /knowledge /arena /cast /docs /docs.html; do
  # a fresh deploy can answer 404 for a new path for a few seconds
  for _ in 1 2 3 4 5 6; do
    CODE=$(curl -sL -o /dev/null -w '%{http_code}' "https://glyph.fru.dev$p")
    [ "$CODE" = "200" ] && break
    sleep 5
  done
  if [ "$CODE" != "200" ]; then
    echo "glyph.fru.dev$p answered $CODE, expected 200"
    exit 1
  fi
done
for p in /dictate /mobile /record /record/ /dictate/; do
  # a fresh deploy's redirects can take a few seconds to answer
  for _ in 1 2 3 4 5 6; do
    TO=$(curl -s -o /dev/null -w '%{redirect_url}' "https://glyph.fru.dev$p")
    [ "$TO" = "https://glyph.fru.dev/jot" ] && break
    sleep 5
  done
  if [ "$TO" != "https://glyph.fru.dev/jot" ]; then
    echo "glyph.fru.dev$p redirects to '$TO', expected /jot"
    exit 1
  fi
done
# Glyph Code became Glyph Rig (2026-10-25): the old page keeps working.
for p in /code /code/; do
  for _ in 1 2 3 4 5 6; do
    TO=$(curl -s -o /dev/null -w '%{redirect_url}' "https://glyph.fru.dev$p")
    [ "$TO" = "https://glyph.fru.dev/rig" ] && break
    sleep 5
  done
  if [ "$TO" != "https://glyph.fru.dev/rig" ]; then
    echo "glyph.fru.dev$p redirects to '$TO', expected /rig"
    exit 1
  fi
done
echo "live at https://glyph.fru.dev"
