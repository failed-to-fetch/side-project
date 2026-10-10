// Deploys Main to the server on every push. Use with a Multibranch Pipeline job
// (or a Pipeline job for Main only). See "Deploying with Jenkins" in README.md.
pipeline {
    agent any

    triggers {
        // Needs the GitHub plugin and a webhook on the repo. If Jenkins isn't
        // reachable from the internet, use polling instead: pollSCM('H/5 * * * *')
        githubPush()
    }

    options {
        disableConcurrentBuilds()      // never run two deploys at once
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        // Set these as global env vars in Jenkins (Manage Jenkins > System),
        // or replace the defaults here.
        DEPLOY_HOST = "${env.DEPLOY_HOST ?: 'ubuntu@79.72.88.229'}"
        DEPLOY_DIR  = "${env.DEPLOY_DIR ?: '/home/ubuntu/side-project'}"
    }

    stages {
        stage('Deploy') {
            when { branch 'Main' }
            steps {
                // SSH private key stored in Jenkins credentials with this ID.
                sshagent(credentials: ['side-project-deploy-ssh']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=accept-new "$DEPLOY_HOST" \
                            "cd '$DEPLOY_DIR' && scripts/deploy.sh '$GIT_COMMIT'"
                    '''
                }
            }
        }
    }

    post {
        failure {
            echo "Deploy of ${env.GIT_COMMIT} failed. On the server: docker compose ps -a, then docker compose logs <service>."
        }
    }
}
