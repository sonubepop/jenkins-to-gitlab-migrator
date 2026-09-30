# jenkins2gitlab

[![CI](https://github.com/sonubepop/jenkins-to-gitlab-migrator/actions/workflows/ci.yml/badge.svg)](https://github.com/sonubepop/jenkins-to-gitlab-migrator/actions/workflows/ci.yml)

Convert **declarative Jenkinsfiles** into **`.gitlab-ci.yml`** and get a checklist of everything that still needs a
human. Built to speed up Jenkins → GitLab CI/CD migrations across many repositories.

**Try it in the browser:** https://sonubepop.github.io/jenkins-to-gitlab-migrator/ (runs locally with Pyodide, nothing is uploaded)

## Why

Migrating dozens of Jenkins jobs by hand is slow and inconsistent. Most of a declarative pipeline maps
mechanically to GitLab CI (stages, parallel jobs, `when` conditions, artifacts, test reports), while a few things
really need a decision (credentials, Groovy `script` blocks, plugins). This tool does the mechanical part and
lists the rest, so every migrated project ends up with the same structure and nothing is silently dropped.

## Quick start

```bash
pip install git+https://github.com/sonubepop/jenkins-to-gitlab-migrator
jenkins2gitlab Jenkinsfile -o .gitlab-ci.yml --report migration-report.md

# or with Docker
docker run --rm -v "$PWD:/work" ghcr.io/sonubepop/jenkins-to-gitlab-migrator Jenkinsfile
```

`--strict` exits with code 2 if anything needs manual review, which is useful in a batch migration script.

## What it converts

| Jenkins (declarative) | GitLab CI |
|---|---|
| `stages` / `stage` | `stages:` + one job per stage |
| `parallel { stage ... }` | jobs in the same stage |
| `matrix { axes { ... } }` | `parallel: matrix:` |
| `agent { docker { image ... } }` / `agent { label ... }` | `image:` / `tags:` |
| `environment { ... }` | `variables:` (credentials are **never** copied - reported instead) |
| `parameters { string / choice / booleanParam }` | prefilled pipeline `variables:` with `description` and `options` |
| `when { branch / tag / environment / changeRequest / changeset / not / anyOf / allOf }` | `rules: - if:` / `changes:` |
| `input` | `when: manual` |
| `options { timeout / retry }`, `timeout {}`, `retry(n) {}` | `timeout:`, `retry:` (capped at GitLab's max of 2) |
| `sh`, `echo`, `dir`, `withEnv`, `sleep`, `error` | `script:` lines |
| `archiveArtifacts`, `stash` | `artifacts: paths:` |
| `junit` | `artifacts: reports: junit:` |
| stage `post { always / success / failure }` | `after_script:` with `$CI_JOB_STATUS` checks |
| pipeline `post { always / success / failure }` | jobs in the `.post` stage |
| stage that only installs dependencies | `default: before_script:` (GitLab jobs don't share a workspace) |
| `$BUILD_NUMBER`, `${env.BRANCH_NAME}`, `$GIT_COMMIT`, ... | `$CI_PIPELINE_IID`, `$CI_COMMIT_REF_NAME`, `$CI_COMMIT_SHA`, ... |

Reported for manual review: `credentials()` / `withCredentials` (→ masked CI/CD variables or Vault),
Groovy `script {}` blocks, `when { expression {} }`, `cron` triggers (→ pipeline schedules),
`disableConcurrentBuilds` (→ `resource_group`), docker-in-docker needs, `build job:` (→ downstream pipelines),
and any unknown plugin step.

## Example

[`examples/python-service.Jenkinsfile`](examples/python-service.Jenkinsfile) →
[`examples/python-service.gitlab-ci.yml`](examples/python-service.gitlab-ci.yml) +
[`migration report`](examples/python-service.migration-report.md)

## Dogfooding

This project was itself migrated from Jenkins to GitLab CI with this tool:
[`Jenkinsfile`](Jenkinsfile) → [`.gitlab-ci.yml`](.gitlab-ci.yml). The walkthrough, including the manual fixes,
is in [docs/self-migration.md](docs/self-migration.md).

## Quality checks

- 30 unit tests (parser, converter, CLI) run on Python 3.10 and 3.12
- every generated example **and** the hand-written `.gitlab-ci.yml` are validated against GitLab's official CI JSON
  schema (`check-jsonschema --builtin-schema vendor.gitlab-ci`), and CI fails if committed examples drift
- Dockerfile linted with hadolint; the image runs as a non-root user and is smoke-tested in CI

## Project layout

```
jenkins2gitlab/   parser.py (Jenkinsfile block parser), converter.py (mapping rules),
                  yamlout.py (dependency-free YAML writer), cli.py
tests/            pytest suite
examples/         input Jenkinsfiles + generated .gitlab-ci.yml + migration reports
web/              browser demo (Pyodide) deployed to GitHub Pages / GitLab Pages
.gitlab-ci.yml    this project's own GitLab pipeline;  .github/workflows/ the GitHub mirror of it
```

## Limitations

Scripted pipelines (`node { ... }`) and shared libraries are not supported - the tool stops with a clear message.
The output is a strong starting point, not a guarantee: always review the manual items and run the pipeline once.

## License

MIT
