// The "legacy" Jenkins pipeline this project started with.
// .gitlab-ci.yml is its migrated replacement - see docs/self-migration.md.
pipeline {
    agent { docker { image 'python:3.12-slim' } }
    options {
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
    }
    environment {
        PIP_CACHE_DIR = '.pip-cache'
    }
    stages {
        stage('Install') {
            steps {
                sh 'pip install -e ".[dev]"'
            }
        }
        stage('Checks') {
            parallel {
                stage('Lint') {
                    steps {
                        sh 'ruff check .'
                    }
                }
                stage('Unit tests') {
                    steps {
                        sh 'pytest --junitxml=reports/junit.xml --cov=jenkins2gitlab --cov-report=xml:reports/coverage.xml'
                    }
                    post {
                        always {
                            junit 'reports/junit.xml'
                        }
                    }
                }
            }
        }
        stage('Validate examples') {
            steps {
                sh './scripts/validate-examples.sh'
            }
        }
        stage('Build image') {
            when { branch 'main' }
            agent { label 'docker' }
            steps {
                withCredentials([usernamePassword(credentialsId: 'registry', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                    sh """
                        echo "\$REG_PASS" | docker login -u "\$REG_USER" --password-stdin registry.example.com
                        docker build -t registry.example.com/jenkins2gitlab:${BUILD_NUMBER} .
                        docker push registry.example.com/jenkins2gitlab:${BUILD_NUMBER}
                    """
                }
            }
        }
    }
    post {
        failure {
            echo "Pipeline failed for ${env.BRANCH_NAME}"
        }
    }
}
