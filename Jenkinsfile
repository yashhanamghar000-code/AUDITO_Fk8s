pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        DOCKER_IMAGE = 'yashhanamghar/audito-llm-service'
        IMAGE_TAG = "${BUILD_NUMBER}"
        K8S_NAMESPACE = 'audito'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh 'docker build -t $DOCKER_IMAGE:$IMAGE_TAG add-ai-llm-service'
            }
        }

        stage('Push') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKERHUB_USERNAME',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        set +x
                        echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
                        docker push "$DOCKER_IMAGE:$IMAGE_TAG"
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG'),
                    string(credentialsId: 'anthropic-api-key', variable: 'ANTHROPIC_API_KEY'),
                    file(credentialsId: 'audito-tls-crt', variable: 'TLS_CERT'),
                    file(credentialsId: 'audito-tls-key', variable: 'TLS_KEY')
                ]) {
                    sh '''
                        set +x
                        kubectl apply -f k8s/namespace.yaml
                        kubectl -n "$K8S_NAMESPACE" create secret generic llm-service-secret \
                          --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
                          --dry-run=client -o yaml | kubectl apply -f -
                        kubectl -n "$K8S_NAMESPACE" create secret tls audito-tls \
                          --cert="$TLS_CERT" --key="$TLS_KEY" \
                          --dry-run=client -o yaml | kubectl apply -f -
                        kubectl apply -f k8s/llm-service-config.yaml
                        kubectl apply -f k8s/llm-service.yaml
                        kubectl apply -f k8s/ingress.yaml
                        kubectl -n "$K8S_NAMESPACE" set image deployment/llm-service \
                          llm-service="$DOCKER_IMAGE:$IMAGE_TAG"
                        kubectl -n "$K8S_NAMESPACE" rollout status deployment/llm-service --timeout=5m
                    '''
                }
            }
        }

        stage('Verify') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        kubectl -n "$K8S_NAMESPACE" get pods
                        kubectl -n "$K8S_NAMESPACE" get ingress audito-ingress
                    '''
                }
            }
        }
    }

    post {
        always {
            deleteDir()
        }
    }
}
