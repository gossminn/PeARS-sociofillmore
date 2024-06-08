# PeARS-Federated Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
   - [Creating a Server](#creating-a-server)
     - [Hetzner](#hetzner)
     - [Scaleway](#scaleway)
   - [Deploying Docker and Docker Compose](#deploying-docker-and-docker-compose)
   - [Installing Vim](#installing-vim)
2. [Setup](#setup)
   - [Setting Up the Deployment Directory](#setting-up-the-deployment-directory)
   - [Downloading and Configuring the Docker Compose Files](#downloading-and-configuring-the-docker-compose-files)
3. [Deploy](#deploy)
   - [Bringing Up the Docker Compose](#bringing-up-the-docker-compose)
4. [Management](#management)
   - [Hosting Multiple Pods on the Same Server](#hosting-multiple-pods-on-the-same-server)
   - [Backing Up Data](#backing-up-data)

## Prerequisites

### Creating a Server

To deploy PeARS-federated pod, you need to start by creating a server. Below are instructions for creating a server on Hetzner and Scaleway.

#### Hetzner

1. Visit [Hetzner](https://www.hetzner.com/cloud).
2. Create an account and log in.
3. Follow the [Hetzner Cloud Quickstart Guide](https://docs.hetzner.com/cloud/getting-started/quickstart/) to create a new server.

#### Scaleway

1. Visit [Scaleway](https://www.scaleway.com/).
2. Create an account and log in.
3. Follow the [Scaleway Getting Started Guide](https://www.scaleway.com/en/docs/compute/instances/quickstart/) to create a new server.

### Deploying Docker and Docker Compose

The following instructions are for Ubuntu. For other distributions, refer to the [official Docker documentation](https://docs.docker.com/engine/install/).

1. SSH into your server.
2. Install necessary packages and Docker:
    ```bash
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

### Installing Vim

Install Vim for editing configuration files:

    ```bash
    sudo apt-get install -y vim
    ```

## Setup

### Setting Up the Deployment Directory

1. SSH into your server.
2. Create a directory to store your instance details and to store persistent data for the instance:
    ```bash
    mkdir -p ~/pears-federated/data
    cd ~/pears-federated
    ```

### Downloading and Configuring the Docker Compose Files

1. Download the `docker-compose.yml` and `env-template` files from the GitHub repository:
    ```bash
    wget https://raw.githubusercontent.com/PeARSearch/PeARS-federated/86be9ef98ee5d789a24c01711684bee87aa9fdca/deployment/docker-compose.yaml
    wget https://raw.githubusercontent.com/PeARSearch/PeARS-federated/86be9ef98ee5d789a24c01711684bee87aa9fdca/deployment/.env-template -O .env
    ```
2. Update the values in the `.env` file to match your configuration ( Follow the instructions in the .env file to fill in the data):
    ```bash
    vim .env
    ```

## Deploy

### Bringing Up the Docker Compose

Start the Docker Compose services:
    ```bash
    docker compose up -d
    ```
Optionally, you can specify a PaARS federated pod name:
    ```bash
    docker compose -p pears_federated_pod_name up -d
    ```

## Management

### Hosting Multiple Pods on the Same Server

If you want to host another pod on the same server:

1. Copy the whole project directory to another name corresponding to the domain:
    ```bash
    cp -r ~/pears-federated ~/pears-federated-newdomain
    cd ~/pears-federated-newdomain
    ```
2. Change the environment details in the `.env` file:
    ```bash
    vim .env
    ```
3. Bring it up with the project name as the domain name:
    ```bash
    docker compose -p new_domain_name up -d
    ```

### Backing Up Data

To avoid loss of data, regularly back up the `data` folder:

1. Create a backup directory:
    ```bash
    mkdir -p ~/pears-federated-backups
    ```
2. Copy the data directory to the backup directory:
    ```bash
    cp -r ~/pears-federated/data ~/pears-federated-backups/data_backup_$(date +%Y%m%d%H%M%S)
    ```

Regularly schedule this backup process using a cron job or other automation tools to ensure your data is safe. You can setup configurations to upload these directory to a remote cloud storage for maximum security.

