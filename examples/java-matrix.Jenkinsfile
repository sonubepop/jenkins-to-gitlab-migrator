pipeline {
    agent none
    parameters {
        choice(name: 'TARGET_ENV', choices: ['dev', 'qa', 'prod'], description: 'Where to deploy')
        booleanParam(name: 'RUN_SLOW_TESTS', defaultValue: false, description: 'Run slow integration tests')
    }
    stages {
        stage('Build') {
            agent { docker { image 'maven:3.9-eclipse-temurin-17' } }
            steps {
                sh 'mvn -B -DskipTests package'
                archiveArtifacts artifacts: 'target/*.jar', fingerprint: true
            }
        }
        stage('Test') {
            matrix {
                agent { docker { image 'maven:3.9-eclipse-temurin-17' } }
                axes {
                    axis {
                        name 'JDK'
                        values '17', '21'
                    }
                }
                stages {
                    stage('Test on JDK') {
                        steps {
                            sh 'mvn -B test'
                        }
                    }
                }
            }
        }
        stage('Integration') {
            when {
                allOf {
                    branch 'release/*'
                    environment name: 'RUN_SLOW_TESTS', value: 'true'
                }
            }
            agent { docker { image 'maven:3.9-eclipse-temurin-17' } }
            steps {
                dir('integration') {
                    sh 'mvn -B verify'
                }
            }
            post {
                failure {
                    sh 'cat target/failsafe-reports/*.txt || true'
                }
            }
        }
    }
}
