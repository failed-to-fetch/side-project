// Deploys Main to the server on every push. See "Deploying with Jenkins" in
// README.md. Pushes trigger the job through the job's own configuration (the
// branch source webhook in a Multibranch Pipeline), not from this file.
pipeline {
    agent any

    parameters {
        string(
            name: 'DEPLOY_REF',
            defaultValue: '',
            trim: true,
            description: 'Manual runs: a branch name or commit to deploy instead of Main. ' +
                         'Leave empty to deploy the commit this build checked out.'
        )
    }

    options {
        disableConcurrentBuilds()      // never run two deploys at once
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        // Set these as global env vars in Jenkins (Manage Jenkins > System),
        // or replace the defaults here.
        //   DEPLOY_HOST empty: deploy on the Jenkins machine itself
        //   DEPLOY_HOST=user@host: deploy on another machine over SSH
        //   DEPLOY_DIR: the app's checkout on the target (where .env lives)
        DEPLOY_HOST = "${env.DEPLOY_HOST ?: ''}"
        DEPLOY_DIR  = "${env.DEPLOY_DIR ?: '/home/ubuntu/side-project'}"
    }

    stages {
        stage('Deploy') {
            // Runs for Main (BRANCH_NAME in Multibranch jobs, GIT_BRANCH in plain
            // Pipeline jobs), or for any build where DEPLOY_REF was given.
            when {
                anyOf {
                    branch 'Main'
                    expression { env.GIT_BRANCH == 'origin/Main' }
                    expression { return params.DEPLOY_REF ? true : false }
                }
            }
            steps {
                script {
                    def ref = params.DEPLOY_REF ?: env.GIT_COMMIT
                    // The ref ends up in a shell command on the target, so allow
                    // only characters that can appear in branch names and SHAs.
                    if (!(ref ==~ /[A-Za-z0-9._\/-]+/)) {
                        error "DEPLOY_REF '${ref}' contains characters that aren't allowed in a branch name."
                    }
                    currentBuild.description = "Deploy ${ref}"
                    withEnv(["TARGET_REF=${ref}"]) {
                        if (env.DEPLOY_HOST) {
                            // SSH private key stored in Jenkins credentials with this ID.
                            sshagent(credentials: ['side-project-deploy-ssh']) {
                                sh '''
                                    ssh -o StrictHostKeyChecking=accept-new "$DEPLOY_HOST" \
                                        "cd '$DEPLOY_DIR' && scripts/deploy.sh '$TARGET_REF'"
                                '''
                            }
                        } else {
                            sh 'cd "$DEPLOY_DIR" && scripts/deploy.sh "$TARGET_REF"'
                        }
                    }
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
