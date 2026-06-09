# Jenkins with Docker-in-Docker (DinD) for MLOps CI/CD
#
# Build: docker build -t jenkins-dind -f deploy/jenkins/Dockerfile .
# Run:   docker run -d --name jenkins-dind --privileged \
#              -p 8080:8080 -p 50000:50000 \
#              -v /var/run/docker.sock:/var/run/docker.sock \
#              -v jenkins_home:/var/jenkins_home \
#              jenkins-dind

FROM jenkins/jenkins:lts

USER root

# Install Docker CLI + prerequisites
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        apt-transport-https ca-certificates curl gnupg \
        software-properties-common && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/debian bullseye stable" \
        > /etc/apt/sources.list.d/docker.list && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add Jenkins user to the docker group
RUN groupadd -f docker && usermod -aG docker jenkins

VOLUME /var/lib/docker

USER jenkins
