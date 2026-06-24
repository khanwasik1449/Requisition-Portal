pipeline {
    agent any

    environment {
        PROJECT_DIR = 'requisition_portal'
        PYTHON = 'python3'
        DJANGO_SETTINGS_MODULE = 'requisition_portal.settings'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Environment') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint & Checks') {
            steps {
                sh '''
                    . venv/bin/activate
                    cd $PROJECT_DIR
                    python3 manage.py check --deploy 2>&1 || true
                    python3 manage.py check 2>&1
                '''
            }
        }

        stage('Collect Static Files') {
            steps {
                sh '''
                    . venv/bin/activate
                    cd $PROJECT_DIR
                    python3 manage.py collectstatic --noinput
                '''
            }
        }

        stage('Run Migrations') {
            steps {
                sh '''
                    . venv/bin/activate
                    cd $PROJECT_DIR
                    python3 manage.py migrate --run-syncdb 2>&1 || python3 manage.py migrate
                '''
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    echo "Deploying to production..."
                    # Restart gunicorn service
                    sudo systemctl restart requisition_portal.service || true
                    sudo systemctl reload nginx || true
                '''
            }
        }
    }

    post {
        failure {
            emailext(
                subject: "CI/CD Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Pipeline failed. Check ${env.BUILD_URL} for details.",
                to: "${env.CHANGE_AUTHOR_EMAIL ?: 'admin@example.com'}"
            )
        }
        success {
            echo "Pipeline completed successfully."
        }
    }
}
