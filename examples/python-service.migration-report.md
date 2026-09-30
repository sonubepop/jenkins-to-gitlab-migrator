# Migration report for `examples/python-service.Jenkinsfile`

- Stages: 4
- Jobs: 6
- Converted automatically: 16
- Need manual review: 5

## Manual review

- [ ] **pipeline**: credential 'deploy-token' used as DEPLOY_TOKEN - create a masked/protected CI/CD variable named DEPLOY_TOKEN in Settings > CI/CD > Variables (or read it from Vault)
- [ ] **pipeline.options**: disableConcurrentBuilds - add 'resource_group' to deploy jobs, or enable 'auto-cancel redundant pipelines'
- [ ] **pipeline.triggers**: cron -> create a pipeline schedule '0 2 * * 1-5' (Build > Pipeline schedules)
- [ ] **stage 'Build image'**: job runs docker commands - use a runner with Docker access, or image: docker:27 with services: [docker:27-dind]
- [ ] **stage 'Deploy to staging'**: withCredentials(kubeconfig-staging) - create File-type CI/CD variable(s) KUBECONFIG (or fetch them from Vault with 'secrets:')

## Automatic conversions

- pipeline: docker agent -> image: python:3.12-slim
- pipeline: environment -> variables (APP_NAME, REGISTRY)
- pipeline.options: timeout -> default timeout 30 minutes
- pipeline.options: buildDiscarder -> use artifacts:expire_in and project retention settings
- stage 'Checkout': checkout scm dropped - GitLab clones the repository automatically
- stage 'Checkout': stage has nothing left to run in GitLab - job dropped
- stage 'Install': dependency-install stage moved to default:before_script - Jenkins stages share a workspace but every GitLab job starts clean
- stage 'Unit tests' post.always: junit -> artifacts:reports:junit (shown in merge requests)
- stage 'Quality': parallel -> jobs in the same stage run in parallel
- stage 'Build image': agent label 'docker' -> runner tag
- stage 'Deploy to staging': when -> rules
- stage 'Deploy to production': when -> rules
- stage 'Deploy to production': input -> when: manual (approve by clicking 'play' in the pipeline)
- stage 'Deploy to production': retry(3) -> retry: 2
- pipeline post.failure: -> job in .post stage with when: on_failure
- pipeline post.always: cleanWs dropped - runners start from a clean checkout
