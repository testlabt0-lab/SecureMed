# TLS certificates for the nginx proxy (profile "tls").

Place exactly two files here before starting the profile:

- `fullchain.pem` — the server certificate plus intermediate chain
- `privkey.pem` — the private key (chmod 600; never commit real keys)

Obtain them with any ACME client, e.g. certbot:

    sudo certbot certonly --standalone -d securemed.example.com
    sudo cp /etc/letsencrypt/live/securemed.example.com/{fullchain,privkey}.pem .

Set the matching DNS name in `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` in
`backend/.env.docker`, and `FRONTEND_URL` so password-reset links point at
the same origin.

Renewal: certificates expire — automate re-copying renewed files and
`docker compose restart nginx` (or run certbot on the host with a renewal
hook).
