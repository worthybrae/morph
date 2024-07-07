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

## production setup

### setup digital ocean droplet

```
ssh -i PATH_TO_PRIVATE_SSH_KEY root@DROPLET_IP_ADDRESS
snap install docker
git clone https://github.com/worthybrae/morph.git
```
