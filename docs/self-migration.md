# Migrating this project's own pipeline

This repository started with a Jenkins pipeline ([`Jenkinsfile`](../Jenkinsfile)).
I migrated it to GitLab CI using the tool itself, then finished the remaining items by hand.
The result is [`.gitlab-ci.yml`](../.gitlab-ci.yml).

## Step 1 - automatic conversion

```bash
python -m jenkins2gitlab Jenkinsfile -o .gitlab-ci.yml --report migration-report.md
# converted: 9 automatic, 3 need manual review
```

Converted automatically:

| Jenkins | GitLab CI |
|---|---|
| `agent { docker { image 'python:3.12-slim' } }` | `default: image: python:3.12-slim` |
| `options { timeout(time: 20, unit: 'MINUTES') }` | `default: timeout: 20 minutes` |
| `stage('Install') { sh 'pip install ...' }` | `default: before_script` - Jenkins stages share one workspace, GitLab jobs start clean, so a separate install job would not help later jobs |
| `parallel { stage('Lint') ... stage('Unit tests') ... }` | two jobs in the same `check` stage |
| `junit 'reports/junit.xml'` in `post { always }` | `artifacts: reports: junit` with `when: always` - test results show up in merge requests |
| `when { branch 'main' }` | `rules: - if: $CI_COMMIT_BRANCH == "main"` |
| `agent { label 'docker' }` | `tags: [docker]` |
| `${BUILD_NUMBER}`, `${env.BRANCH_NAME}` | `${CI_PIPELINE_IID}`, `${CI_COMMIT_REF_NAME}` |
| pipeline `post { failure { ... } }` | job in the `.post` stage with `when: on_failure` |

## Step 2 - manual review (from the report)

- [x] **`disableConcurrentBuilds()`** - added `resource_group: registry` to the image job so two pushes never
      race each other, and `interruptible: true` so redundant pipelines get cancelled.
- [x] **`withCredentials([usernamePassword(credentialsId: 'registry', ...)])`** - not needed any more:
      GitLab provides `$CI_REGISTRY_USER` / `$CI_REGISTRY_PASSWORD` for the built-in container registry,
      so no long-lived secret is stored at all.
- [x] **docker commands** - switched the job to `image: docker:27` with the `docker:27-dind` service and TLS
      (`DOCKER_TLS_CERTDIR`), so it runs on shared runners instead of needing a special `docker` label.

## Step 3 - improvements that were not in the Jenkins pipeline

- `workflow: rules` to avoid duplicate branch + merge request pipelines
- pip cache keyed on `pyproject.toml`
- coverage percentage parsed from the log and a Cobertura report for MR diff coverage
- image tagged with the commit SHA, plus `latest` only on the default branch
- `pages` job that publishes the browser demo to GitLab Pages
- `validate-examples` job that checks every generated file against GitLab's official CI JSON schema
  and fails if the committed examples drift from the tool's output
