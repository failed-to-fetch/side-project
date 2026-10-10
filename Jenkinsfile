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
        // Every branch: prove all production images still build (the frontend
        // image also runs its TypeScript compile). This is what makes the Jenkins
        // check on a pull request mean something, and a broken image stops a Main
        // deploy before the server is touched. Uses the Docker socket Jenkins
        // already has; shared layers also warm the cache the deploy uses.
        stage('Build images') {
            steps {
                sh '''
                    set -e
                    if ! docker buildx version >/dev/null 2>&1; then
                        echo "docker buildx (BuildKit) is missing where Jenkins runs; the images need it." >&2
                        echo "Install the docker-buildx-plugin package in the Jenkins image." >&2
                        exit 1
                    fi
                    export DOCKER_BUILDKIT=1
                    docker build --target prod -t "side-project-ci-backend:$GIT_COMMIT" backend
                    docker build --target prod -t "side-project-ci-auth:$GIT_COMMIT" services/auth
                    docker build -t "side-project-ci-frontend:$GIT_COMMIT" frontend
                '''
            }
            post {
                // Drop the tags; the layers stay cached for the next build.
                always {
                    sh '''
                        for s in backend auth frontend; do
                            docker image rm "side-project-ci-$s:$GIT_COMMIT" >/dev/null 2>&1 || true
                        done
                    '''
                }
            }
        }

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
                            // SSH private key stored in Jenkins credentials with this ID
                            // (kind: SSH Username with private key). withCredentials
                            // writes it to a temporary file for this block only.
                            withCredentials([sshUserPrivateKey(
                                credentialsId: 'side-project-deploy-ssh',
                                keyFileVariable: 'SSH_KEY'
                            )]) {
                                // deploy.sh updates its own checkout, but it has to
                                // exist there first: a checkout from before it was
                                // added needs one manual update.
                                sh '''
                                    ssh -i "$SSH_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
                                        -o StrictHostKeyChecking=accept-new "$DEPLOY_HOST" \
                                        "cd '$TARGET_DIR' && if [ ! -x scripts/deploy.sh ]; then echo 'scripts/deploy.sh is missing in $TARGET_DIR on the server. Update that checkout once by hand: git fetch origin && git checkout <branch> && git pull' >&2; exit 1; fi && scripts/deploy.sh '$TARGET_REF'"
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
            echo "Deploy failed. The reason is in the Console Output, just after the 'Deploying ...' line. " +
                 "If the deploy itself ran, on the server: docker compose ps -a, then docker compose logs <service>."
        }
    }
}
