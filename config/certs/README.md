If you want to use your own certificates (for caddy and/or keycloak), place them here.

To be consistent with the example docker compose, you would want:
- fullchain.pem   (web server, caddy, see also env var TLS_CERT_FILE)
- privkey.pem     (web server, caddy, see also env var TLS_KEY_FILE)
- custom_ca.crt   (keycloak, see also env var SSL_CERT_FILE)
