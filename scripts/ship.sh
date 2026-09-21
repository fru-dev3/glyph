#!/usr/bin/env bash
#
# Deploy the glyph.fru.dev site (the static files in docs/) to Vercel,
# team fru-dev3, project glyph-fru. No build step, no functions, no secrets.
#
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .vercel/project.json ] || vercel link --yes --project glyph-fru

echo "building"
vercel build --prod --yes

echo "deploying"
vercel deploy --prebuilt --prod

CODE=$(curl -s -o /dev/null -w '%{http_code}' https://glyph.fru.dev/docs)
if [ "$CODE" != "200" ]; then
  echo "glyph.fru.dev/docs answered $CODE, expected 200"
  exit 1
fi
echo "live at https://glyph.fru.dev"
