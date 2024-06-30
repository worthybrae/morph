## Setup

1. Spin up digital ocean droplet with ssh key connection
2. SSH into droplet `ssh -i ~/.ssh/{ENTER SSH PRIVATE KEY LOCATION} root@{ENTER DIGITAL OCEAN IP ADDRESS}`
3. Install docker ```
   sudo apt update
   sudo apt install apt-transport-https ca-certificates curl software-properties-common
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
   sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
   sudo apt update
   sudo apt install docker-ce

   ```


   ```

4.
