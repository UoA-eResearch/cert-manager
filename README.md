# cert-manager
A simple flask web app to act as an orchestration/administrative interface across the blockcert projects / workflow

### Installation

Running this requires a Linux VM with Docker installed (`sudo apt install docker.io`), and ports 80 and 443 open.  

From your home folder on the VM (~):

- `git clone https://github.com/UoA-eResearch/cert-manager.git && pip install -r cert-manager/requirements.txt`
- Follow the instructions on https://github.com/blockchain-certificates/cert-tools/blob/master/README.md to install cert-tools
- Follow the instructions on https://github.com/blockchain-certificates/cert-issuer/blob/master/README.md to build the the cert-issuer Docker container. Particularly, make sure you perform the first-time setup step of creating an issuer (https://github.com/blockchain-certificates/cert-issuer/blob/master/README.md#create-issuing-address)
- `git clone -b uoa https://github.com/UoA-eResearch/cert-viewer.git && cd cert-viewer && docker-compose build && docker-compose up -d`
- Note how https://github.com/UoA-eResearch/cert-viewer/blob/d9c85a68c77af9d2831dacf8f18778388b2a27c0/docker-compose.yml#L10 maps cert-issuer's signed certificates folder into cert-viewer's cert_data filepath, so that cert-viewer displays all certificates signed by cert-issuer.

### Running

`./web_server.py`

This webapp will serve `index.html` via GET requests, and handle POST requests from the form within that HTML. When a POST request is recieved it will:

- Change directory to ~/cert-tools, and call `create-certificate-template` with the provided certificate title
- Save the uploaded CSV of participants to the filesystem
- Call `instantiate-certificate-batch` with the created template + the CSV
- Copy the unsigned certificates to `~/cert-issuer/conf/data/unsigned_certificates`
- Run the cert-issuer docker container to hash these certificates on the Bitcoin Testnet blockchain, as a merkle tree
- Restart the `cert-viewer_web_1` Docker container, so that it picks up the new certificates

Optionally, it will also send email notifications to participants notifying them of their new certificate. If you wish to use this functionality, you will likely need to replace `mailhost.auckland.ac.nz` with your own SMTP mail server. Additionally, you'll need to replace `https://blockcert.auckland.ac.nz/` with your own URL, where cert-viewer is accessible.

The server runs on port 8080 - you can proxy this via Apache, Nginx, Caddy (I recommend Caddy) for HTTPS.
