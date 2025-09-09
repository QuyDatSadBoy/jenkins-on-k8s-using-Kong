pipeline {
    agent any
    
    environment {
        DOCKER_HUB = 'b21dccn222'
        IMAGE_NAME = 'fastapi-k8s'
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${DOCKER_HUB}/${IMAGE_NAME}:${IMAGE_TAG}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'ls -la'
            }
        }
        
        stage('Install Tools') {
            steps {
                script {
                    sh """
                        # Install Docker client if not exists
                        if ! command -v docker &> /dev/null; then
                            apt-get update
                            apt-get install -y docker.io
                        fi
                        
                        # Install kubectl if not exists
                        if ! command -v kubectl &> /dev/null; then
                            curl -LO "https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl"
                            chmod +x kubectl
                            mv kubectl /usr/local/bin/
                        fi
                        
                        docker version
                        kubectl version --client
                    """
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    sh """
                        echo "Building image: ${FULL_IMAGE}"
                        docker build -f docker/Dockerfile -t ${FULL_IMAGE} .
                        docker tag ${FULL_IMAGE} ${DOCKER_HUB}/${IMAGE_NAME}:latest
                        docker images | grep ${IMAGE_NAME}
                    """
                }
            }
        }
        
        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh """
                        echo \${DOCKER_PASS} | docker login -u \${DOCKER_USER} --password-stdin
                        docker push ${FULL_IMAGE}
                        docker push ${DOCKER_HUB}/${IMAGE_NAME}:latest
                        docker logout
                    """
                }
            }
        }
        
        stage('Deploy to K8s') {
            // steps {
            //     script {
            //         sh """
            //             # Update deployment with new image
            //             kubectl set image deployment/fastapi-app fastapi=${FULL_IMAGE} -n fastapi || \
            //             helm upgrade --install fastapi-app ./helm/fastapi -n fastapi --set image.tag=${IMAGE_TAG}
                        
            //             # Wait for rollout
            //             kubectl rollout status deployment/fastapi-app -n fastapi --timeout=120s
                        
            //             # Show deployment info
            //             kubectl get deployment,pods -n fastapi
            //         """

                    
            //     }
            // }

            steps {
            withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
            sh """
                # Export kubeconfig
                export KUBECONFIG=\${KUBECONFIG}
                
                # Update deployment with new image
                kubectl set image deployment/fastapi-app fastapi=${FULL_IMAGE} -n fastapi || \
                helm upgrade --install fastapi-app ./helm/fastapi -n fastapi --set image.tag=${IMAGE_TAG}
                
                # Wait for rollout
                kubectl rollout status deployment/fastapi-app -n fastapi --timeout=120s
                
                # Show deployment info
                kubectl get deployment,pods -n fastapi
            """
        }
        }
        }
        
        stage('Test Deployment') {
            steps {
                script {
                    sh """
                        # Wait for service to be ready
                        sleep 10
                        
                        # Test internal service
                        kubectl run test-curl-\${BUILD_NUMBER} --image=curlimages/curl --rm -i --restart=Never -- \
                            curl -s http://fastapi-app-service.fastapi.svc.cluster.local:8000/health || true
                        
                        echo ""
                        echo "✅ Deployment successful!"
                        echo "Access FastAPI at:"
                        echo "  • http://fastapi.k8s.local:30080/api/docs"
                        echo "  • http://192.168.0.154:30080/api/docs"
                        echo "  • https://6ec0d8ed00b2.ngrok-free.app/api/docs"
                    """
                }
            }
        }
    }
    
    post {
        success {
            echo "CI/CD Pipeline completed successfully!"
            echo "Version ${IMAGE_TAG} deployed"
        }
        failure {
            echo "Pipeline failed! Check logs for details."
        }
        cleanup {
            sh """
                # Clean up Docker images to save space
                docker rmi ${FULL_IMAGE} || true
                docker rmi ${DOCKER_HUB}/${IMAGE_NAME}:latest || true
            """
        }
    }
}