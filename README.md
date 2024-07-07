# morph

custom masks for livestream videos

## dependencies

make sure docker compose is installed

## production setup

### setup digital ocean droplet

```
ssh -i PATH_TO_PRIVATE_SSH_KEY root@DROPLET_IP_ADDRESS
snap install docker
git clone https://github.com/worthybrae/morph.git
```

### local setup

```
docker-compose build --no-cache
docker-compose up -d
```

#
