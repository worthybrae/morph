# morph

custom mask for livestream videos

## local setup

```
docker-compose build --no-cache
docker-compose up -d
```

### dependencies

Before you begin, ensure you have the following installed on your system:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [nginx](https://nginx.org/en/)

## production setup

### create digital ocean droplet

1. create droplet from ubuntu base image
2. specify ssh key for root login
3. ssh into digital ocean droplet once created: `ssh -i PATH_TO_PRIVATE_SSH_KEY root@DROPLET_IP_ADDRESS`
4. install docker / docker-compose: `snap install docker`
5. git clone https://github.com/worthybrae/morph.git
6. update your github secrets to reflect the necessary value in the deploy.yml file

## about
