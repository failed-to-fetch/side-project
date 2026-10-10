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
        //   DEPLOY_HOST=user@host: deploy over SSH. Jenkins in a container on the
        //     same VM: user@host.docker.internal (see README).
        //   DEPLOY_HOST empty: deploy on the Jenkins machine itself (not from
        //     inside a Jenkins container, which can't see the app's files).
        //   DEPLOY_DIR: the app's checkout on the target. Over SSH it may be
        //     relative to the user's home (side-project or ~/side-project).
        DEPLOY_HOST = "${env.DEPLOY_HOST ?: ''}"
        DEPLOY_DIR  = "${env.DEPLOY_DIR ?: 'side-project'}"
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
                    // "~/side-project" -> "side-project": SSH sessions start in
                    // the user's home, and a quoted ~ wouldn't expand anyway.
                    def dir = env.DEPLOY_DIR.replaceFirst(/^~\/?/, '') ?: '.'
                    // Both end up in a shell command on the target, so allow only
                    // characters that appear in branch names, SHAs and paths.
                    if (!(ref ==~ /[A-Za-z0-9._\/-]+/)) {
                        error "DEPLOY_REF '${ref}' contains characters that aren't allowed in a branch name."
                    }
                    if (!(dir ==~ /[A-Za-z0-9._\/-]+/)) {
                        error "DEPLOY_DIR '${env.DEPLOY_DIR}' contains characters that aren't allowed in a path."
                    }
                    if (!env.DEPLOY_HOST && !dir.startsWith('/')) {
                        error "DEPLOY_HOST is empty, so this would deploy inside the Jenkins machine itself. " +
                              "If Jenkins runs in a container on the app's VM, set DEPLOY_HOST=<user>@host.docker.internal. " +
                              "To deploy on the Jenkins machine, set DEPLOY_DIR to an absolute path."
                    }
                    def where = env.DEPLOY_HOST ? "${env.DEPLOY_HOST}:${dir}" : dir
                    echo "Deploying ${ref} to ${where}"
                    currentBuild.description = "Deploy ${ref}"
                    withEnv(["TARGET_REF=${ref}", "TARGET_DIR=${dir}"]) {
                        if (env.DEPLOY_HOST) {
                            // SSH private key stored in Jenkins credentials with this ID.
                            sshagent(credentials: ['side-project-deploy-ssh']) {
                                sh '''
                                    ssh -o StrictHostKeyChecking=accept-new "$DEPLOY_HOST" \
                                        "cd '$TARGET_DIR' && scripts/deploy.sh '$TARGET_REF'"
                                '''
                            }
                        } else {
                            sh 'cd "$TARGET_DIR" && scripts/deploy.sh "$TARGET_REF"'
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
