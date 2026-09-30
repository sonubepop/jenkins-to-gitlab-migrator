#!/usr/bin/env sh
# Regenerate every example and check that
#  1) the output is valid against GitLab's official CI JSON schema
#  2) the committed output is up to date (no drift)
set -eu
for jf in examples/*.Jenkinsfile; do
  base="${jf%.Jenkinsfile}"
  python -m jenkins2gitlab "$jf" -o "$base.gitlab-ci.yml" --report "$base.migration-report.md"
done
python -m jenkins2gitlab Jenkinsfile -o /tmp/self-migrated.gitlab-ci.yml
check-jsonschema --builtin-schema vendor.gitlab-ci examples/*.gitlab-ci.yml /tmp/self-migrated.gitlab-ci.yml .gitlab-ci.yml
git diff --exit-code -- examples/ || { echo "examples are out of date - run scripts/validate-examples.sh and commit"; exit 1; }
