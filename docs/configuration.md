## ⚙️ Configuration

### Environment Variables

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `superset` |
| `POSTGRES_USER` | Database user | `superset` |
| `POSTGRES_PASSWORD` | Database password | **Required** |
| `REDIS_PASSWORD` | Redis password | **Required** |
| `SUPERSET_ADMIN` | Admin username | `admin` |
| `SUPERSET_PASSWORD` | Admin password | **Required** |
| `SUPERSET_SECRET_KEY` | Secret key for sessions | **Required** |
| `AUTH_TYPE` | Authentication backend (`AUTH_DB` or `AUTH_OAUTH`) | `AUTH_DB` |
| `SUPERSET_LOAD_EXAMPLES` | Load example data | `no` |


### SMTP Configuration

For email alerts and reports, add to `.env`:

```bash
SMTP_HOST=smtp.yourdomain.com
SMTP_STARTTLS=True
SMTP_SSL=False
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_PORT=587
SMTP_MAIL_FROM=superset@yourdomain.com
```

### Custom Assets

Place custom images, logos, or assets:
```
docker/superset/assets/images/
```
They will be copied during container build, and available in superset under
`/static/assets/images/`. They cannot be changed at runtime.

Alternatively, we also mount the `./assets` folder to
`/app/superset/static/assets/custom` in the Superset container, so you can
place assets at runtime and reference them in superset via `/static/assets/custom/...`.

### Role-Based Redirect Landing Pages

Superset can send different roles to different dashboards at login. To enable it:

1. Set `USE_ROLE_BASED_REDIRECTS=true` in `.env`.
2. Adjust the `ROLE_BASED_REDIRECTS` dictionary inside [superset/superset_config.py](superset/superset_config.py) so each role points to the desired URL.
3. (Requirement) Role-based redirects rely on an OAuth identity provider because they execute after federated login; Keycloak is currently supported out of the box.

### Superset Configuration

The `superset_config.py` file contains:
- Database connection settings
- Redis cache configuration
- Celery task queue settings
- Feature flags
- Security settings

### Translation Fixes (Superset 5.x)

Superset 5.0.0 (and 6.0.0) ships with a German translation regression. Follow the steps in [translations/README.md](translations/README.md) to patch the locale bundle before building the image if you need the corrected strings.

### Authentication Modes

- `AUTH_DB` (default) keeps Superset's built-in username/password login and does not require any Keycloak services.
- `AUTH_OAUTH` enables Keycloak SSO. When you choose this mode:
   1. Copy [auth/keycloak/keycloak_clients.sample.yml](auth/keycloak/keycloak_clients.sample.yml) to [auth/keycloak/keycloak_clients.yml](auth/keycloak/keycloak_clients.yml).
   2. Fill in the Keycloak host, realm, client ID, and client secret, then set `AUTH_TYPE=AUTH_OAUTH` in `.env`.
   3. Ensure the Keycloak stack is running (the provided [docker-compose-keycloak.yml](docker-compose-keycloak.yml) is an optional local test helper, not a production deployment) and restart the Superset services so the new credentials are picked up.

### Adding Custom Packages

Edit `Dockerfile` to add additional Python packages:

```dockerfile
RUN uv pip install --system your-package==version
```

### Reverse Proxy TLS (Caddy)

This repo includes an optional Caddy reverse proxy setup in [docker-compose.caddy.yml](docker-compose.caddy.yml).

#### Self-signed mode (client trust required)

If you run with `TLS_MODE=selfsigned`, Caddy generates a private Root + Intermediate CA ("linkFISH Consulting CA") and issues the site certificate from that CA.
Clients must trust the generated **Root CA certificate** to avoid browser/OS TLS warnings.

1) Export the generated CA certificates from the Caddy data volume:

```powershell
# From the repo folder (where docker-compose.caddy.yml is)

# Root CA (recommended to trust on clients)
docker run --rm -v superset_caddy_data:/data -v "${PWD}:/out" alpine:3.20 sh -ec "cp /data/caddy/pki/authorities/linkfish/root.crt /out/linkfish-root-ca.crt"

# Intermediate CA (usually not required to trust explicitly)
docker run --rm -v superset_caddy_data:/data -v "${PWD}:/out" alpine:3.20 sh -ec "cp /data/caddy/pki/authorities/linkfish/intermediate.crt /out/linkfish-intermediate-ca.crt"
```

2) Import on clients:

- Windows (trust Root CA):

```powershell
certutil -addstore -f Root linkfish-root-ca.crt
```

- Linux (Debian/Ubuntu):

```bash
sudo cp linkfish-root-ca.crt /usr/local/share/ca-certificates/linkfish-root-ca.crt
sudo update-ca-certificates
```

- Linux (RHEL/Fedora/CentOS):

```bash
sudo cp linkfish-root-ca.crt /etc/pki/ca-trust/source/anchors/linkfish-root-ca.crt
sudo update-ca-trust
```

- macOS / iOS

1. Copy `linkfish-root-ca.crt` to your Mac/iPhone.
2. Install on macOS via double‑click → Keychain → System → Always Trust.
3. Install on iOS as a profile, then go to:
Settings → General → About → Certificate Trust Settings → enable full trust for `linkfish-root-ca.crt`.


Notes:
- You normally only need to import the **root** CA; Caddy serves the intermediate as part of the certificate chain.
- After installing, restart your browser/app so it reloads the system trust store.

#### Reuse the same CA on another Caddy instance (advanced)

If you want a second Caddy instance to issue certificates from the **same** internal CA (so clients only have to trust one Root CA), you can export and import the CA material.

Important:
- This exports **private keys** (`root.key`, `intermediate.key`). Treat them like production secrets.
- Never distribute these keys to clients. Clients should only receive the CA **certificates** (`.crt`).
- If the target Caddy already generated its own CA, stop it and replace the CA files before restarting.

1) Export CA certificates + private keys from the source Caddy data volume:

```powershell
# Creates 4 files in the current folder:
# - linkfish-root-ca.crt
# - linkfish-root-ca.key
# - linkfish-intermediate-ca.crt
# - linkfish-intermediate-ca.key
docker run --rm -v superset_caddy_data:/data -v "${PWD}:/out" alpine:3.20 sh -ec "\
   cp /data/caddy/pki/authorities/linkfish/root.crt /out/linkfish-root-ca.crt && \
   cp /data/caddy/pki/authorities/linkfish/root.key /out/linkfish-root-ca.key && \
   cp /data/caddy/pki/authorities/linkfish/intermediate.crt /out/linkfish-intermediate-ca.crt && \
   cp /data/caddy/pki/authorities/linkfish/intermediate.key /out/linkfish-intermediate-ca.key"
```

2) Securely transfer those 4 files to the machine that will run the other Caddy instance.

3) Import them into the target Caddy data volume (before starting Caddy):

```powershell
docker run --rm \
   -v <TARGET_CADDY_DATA_VOLUME>:/data \
   -v "${PWD}:/in" \
   alpine:3.20 sh -ec "\
      mkdir -p /data/caddy/pki/authorities/linkfish && \
      cp /in/linkfish-root-ca.crt /data/caddy/pki/authorities/linkfish/root.crt && \
      cp /in/linkfish-root-ca.key /data/caddy/pki/authorities/linkfish/root.key && \
      cp /in/linkfish-intermediate-ca.crt /data/caddy/pki/authorities/linkfish/intermediate.crt && \
      cp /in/linkfish-intermediate-ca.key /data/caddy/pki/authorities/linkfish/intermediate.key && \
      chmod 600 /data/caddy/pki/authorities/linkfish/*.key"
```

4) Ensure the target Caddy config uses the same CA id (`ca linkfish`) and start the stack.

### OAuth via Keycloak

#### Preparing Certificates from PFX

If your certificate is in PFX format, extract the components as follows:

```bash
# Private key
openssl pkcs12 -in my_cert.pfx -nocerts -out my_cert_key.pem -nodes

# Certificate + chain
openssl pkcs12 -in my_cert.pfx -nokeys -out my_cert_fullchain.pem

# Root CA (required for Keycloak)
openssl pkcs12 -in my_cert.pfx -cacerts -nokeys -out my_root_ca.pem
openssl x509 -in my_root_ca.pem -out my_root_ca.crt
```

* Configure your `keycloak_clients.yml` as needed.
* If Keycloak uses a custom CA (for outbound HTTPS proxy requests, Keycloak integration, database drivers, etc.), copy the `.crt` content to [auth/keycloak/custom-ca.crt](auth/keycloak/custom-ca.crt).
* * In the .env file, set the following variables. This will tell the flask Apps to trust these certificates:
```bash
REQUESTS_CA_BUNDLE=/app/superset/auth_keycloak/custom-ca.crt
SSL_CERT_FILE=/app/superset/auth_keycloak/custom-ca.crt
```
* Use the docker compose command below afterwards. It will copy all CAs from `./auth/keycloak` to `app/superset/auth_keycloak` which is volume mounted as `superset_keycloak_data`.

Linux:
```bash
docker compose -f docker-compose.yml run --rm --user root \
  -v "./auth/keycloak:/tmp/auth_keycloak:rw" \
  -v superset_keycloak_data:/app/superset/auth_keycloak:rw \
  superset-init sh -c "cp -a /tmp/auth_keycloak/. /app/superset/auth_keycloak/ && chown -R superset:superset /app/superset/auth_keycloak && chmod -R u+rwX,g+rX,o-rwx /app/superset/auth_keycloak"

# Restart the superset app container afterwards
docker compose -f docker-compose.yml restart superset-app
```

Windows:
```bash
docker compose -f docker-compose.yml run --rm --user root `
  -v "./auth/keycloak:/tmp/auth_keycloak:rw" `
  -v superset_keycloak_data:/app/superset/auth_keycloak:rw `
  superset-init sh -c "cp -a /tmp/auth_keycloak/. /app/superset/auth_keycloak/ && chown -R superset:superset /app/superset/auth_keycloak && chmod -R u+rwX,g+rX,o-rwx /app/superset/auth_keycloak"

# Restart the superset app container afterwards
docker compose -f docker-compose.yml restart superset-app
```
Run this command whenever you change the ca certificate or settings  `keycloak_clients.yml`!

### Connecting to external Databses from Superset

For example, for mssql the connection string format is [see here](https://superset.apache.org/docs/configuration/databases/):
```
mssql+pymssql://<Username>:<Password>@<Host>:<Port-default:1433>/<Database Name>
```

If using Docker Desktop, and hosting databases in a separate stack, use
`host.docker.internal` as the hostname to connect to the host machine, and the
ports exposed on the host. (If you added your backend to _this_ stack you can use the
service/container name and the native container ports.)


### Performance Tuning

For production environments:

1. **Increase worker concurrency**:
   Edit `start_celery_worker.sh` to increase `--concurrency`

2. **Adjust gunicorn workers**:
   Edit `start_superset.sh` to increase `--workers`

3. **PostgreSQL tuning**:
   Add custom PostgreSQL configuration

4. **Redis memory**:
   Adjust `maxmemory` in docker compose.yml


### Note on Proxies

**Note for Forward Proxy Users**: If behind a forward proxy, set these environment variables to pull from remote repositories:

```bash
export http_proxy=your-proxy:8080
export https_proxy=your-proxy:8080
export HTTP_PROXY=your-proxy:8080
export HTTPS_PROXY=your-proxy:8080
export all_proxy=your-proxy:8080
```
