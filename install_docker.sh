#!/usr/bin/env bash

echo "Installing Docker"

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-cache policy docker-ce
sudo apt-get -y install docker-ce

echo "Waiting for Docker daemon to start"
sleep 2

if ! docker ps; then
    echo "Trying to fix Docker permissions, you should log-out and back in before starting to use Docker"
    echo "To test the installation immediately, run: su - ${USER}"
    sudo usermod -aG docker "${USER}"
fi

echo "Installing Docker Compose"

sudo curl -o /usr/local/bin/docker-compose -L "https://github.com/docker/compose/releases/download/1.17.1/docker-compose-$(uname -s)-$(uname -m)"
sudo chmod +x /usr/local/bin/docker-compose
docker-compose -v
