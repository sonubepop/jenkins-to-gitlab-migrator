# Migration report for `examples/java-matrix.Jenkinsfile`

- Stages: 3
- Jobs: 3
- Converted automatically: 9
- Need manual review: 0

## Automatic conversions

- pipeline: 'agent none' -> each job chooses its own image
- pipeline.parameters: build parameters -> prefilled pipeline variables (TARGET_ENV, RUN_SLOW_TESTS)
- stage 'Build': docker agent -> image: maven:3.9-eclipse-temurin-17
- stage 'Build': archiveArtifacts -> artifacts:paths target/*.jar
- stage 'Test': matrix -> parallel:matrix over JDK
- stage 'Test': docker agent -> image: maven:3.9-eclipse-temurin-17
- stage 'Integration': when -> rules
- stage 'Integration': docker agent -> image: maven:3.9-eclipse-temurin-17
- stage 'Integration': stage post -> after_script (with $CI_JOB_STATUS checks)
