// Typical Python service pipeline from a Jenkins controller
pipeline {
    agent {
        docker { image 'python:3.12-slim' }
    }
    environment {
        APP_NAME = 'inventory-api'
        REGISTRY = 'registry.example.com/team'
        DEPLOY_TOKEN = credentials('deploy-token')
    }
    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }
    triggers {
        cron('H 2 * * 1-5')
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Install') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        stage('Quality') {
            parallel {
                stage('Lint') {
                    steps {
                        sh 'ruff check .'
                    }
                }
                stage('Unit tests') {
                    steps {
                        sh 'pytest --junitxml=reports/junit.xml'
                    }
                    post {
                        always {
                            junit 'reports/junit.xml'
                        }
                    }
                }
            }
        }
        stage('Build image') {
            agent { label 'docker' }
            steps {
                sh """
                    docker build -t ${REGISTRY}/${APP_NAME}:${BUILD_NUMBER} .
                    docker push ${REGISTRY}/${APP_NAME}:${BUILD_NUMBER}
                """
            }
        }
        stage('Deploy to staging') {
            when { branch 'main' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig-staging', variable: 'KUBECONFIG')]) {
                    sh "kubectl set image deployment/${APP_NAME} app=${REGISTRY}/${APP_NAME}:${BUILD_NUMBER}"
                }
            }
        }
        stage('Deploy to production') {
            when { tag 'v*' }
            input { message 'Deploy to production?' }
            steps {
                retry(3) {
                    sh './scripts/deploy.sh production'
                }
            }
        }
    }
    post {
        failure {
            echo "Build ${BUILD_NUMBER} failed on ${env.BRANCH_NAME}"
        }
        always {
            cleanWs()
        }
    }
}
