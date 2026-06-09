pipeline {
    agent any

    environment {
        VENV_DIR    = 'venv'
        GCP_PROJECT = "mlops-new-447207"
        GCLOUD_PATH = "/var/jenkins_home/google-cloud-sdk/bin"
        IMAGE_NAME  = "gcr.io/${GCP_PROJECT}/hotel-prediction"
        IMAGE_TAG   = "latest"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Cloning repository from GitHub...'
                checkout scmGit(
                    branches: [[name: '*/main']],
                    extensions: [],
                    userRemoteConfigs: [[
                        credentialsId: 'github-token',
                        url: 'https://github.com/data-guru0/MLOPS-COURSE-PROJECT-1.git'
                    ]]
                )
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo 'Setting up virtual environment and installing dependencies...'
                sh '''
                    python -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                withCredentials([file(credentialsId: 'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    echo 'Building Docker image and pushing to GCR...'
                    sh '''
                        export PATH=$PATH:${GCLOUD_PATH}

                        gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project ${GCP_PROJECT}
                        gcloud auth configure-docker --quiet

                        docker build -f deploy/Dockerfile -t ${IMAGE_NAME}:${IMAGE_TAG} .
                        docker push ${IMAGE_NAME}:${IMAGE_TAG}
                    '''
                }
            }
        }

        stage('Deploy to Cloud Run') {
            steps {
                withCredentials([file(credentialsId: 'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    echo 'Deploying to Google Cloud Run...'
                    sh '''
                        export PATH=$PATH:${GCLOUD_PATH}

                        gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project ${GCP_PROJECT}

                        gcloud run deploy hotel-prediction \
                            --image=${IMAGE_NAME}:${IMAGE_TAG} \
                            --platform=managed \
                            --region=us-central1 \
                            --port=8080 \
                            --allow-unauthenticated
                    '''
                }
            }
        }

    }

    post {
        success {
            echo "✅ Pipeline succeeded — image: ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo "❌ Pipeline failed. Check logs above for details."
        }
    }
}