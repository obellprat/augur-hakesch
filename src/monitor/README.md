# Augur Hakesch External Monitor

External monitoring tool that monitors the Augur Hakesch API system metrics and sends email alerts when thresholds are exceeded.

## Features

- Monitors CPU, memory, and disk usage every 5 minutes (configurable)
- Sends email alerts when critical thresholds are exceeded
- 12-hour cooldown between warning emails (configurable)
- Authenticates with Keycloak to access protected monitoring endpoints
- Runs as a Docker container

## Configuration

Copy `.env-example` to `.env` and configure the following variables:

### Keycloak Authentication

**Option 1: Client Credentials (Recommended for service accounts)**
- `KEYCLOAK_URL`: Keycloak server URL (default: https://id.augur.world)
- `KEYCLOAK_REALM`: Keycloak realm (default: augur)
- `KEYCLOAK_CLIENT_ID`: Keycloak client ID
- `KEYCLOAK_CLIENT_SECRET`: Keycloak client secret

**Option 2: Password Grant (Requires Direct Access Grants enabled)**
- `KEYCLOAK_URL`: Keycloak server URL (default: https://id.augur.world)
- `KEYCLOAK_REALM`: Keycloak realm (default: augur)
- `KEYCLOAK_CLIENT_ID`: Keycloak client ID
- `KEYCLOAK_USERNAME`: Keycloak username
- `KEYCLOAK_PASSWORD`: Keycloak password
- `KEYCLOAK_CLIENT_SECRET`: (Optional but recommended) Client secret if client is confidential

**Note:** For password grant, the Keycloak client must have "Direct Access Grants" enabled in the client settings. If the client is confidential, you should also provide `KEYCLOAK_CLIENT_SECRET`.

### API Configuration
- `API_URL`: API base URL (default: http://localhost:8000)
- `API_PATH`: API path prefix (default: /api)

### Monitoring Configuration
- `CHECK_INTERVAL`: Check interval in seconds (default: 300 = 5 minutes)
- `EMAIL_COOLDOWN`: Email cooldown in seconds (default: 43200 = 12 hours)

### Thresholds
- `CPU_CRITICAL`: CPU usage threshold percentage (default: 90.0)
- `MEMORY_CRITICAL`: Memory usage threshold percentage (default: 90.0)
- `DISK_CRITICAL`: Disk usage threshold percentage (default: 90.0)

### SMTP Configuration
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port (default: 587)
- `SMTP_USER`: SMTP username (optional)
- `SMTP_PASSWORD`: SMTP password (optional)
- `SMTP_FROM`: From email address
- `EMAIL_RECIPIENTS`: Comma-separated list of recipient email addresses

## Running with Docker

### Build the image:
```bash
docker build -t augur-monitor ./src/monitor
```

### Run the container:
```bash
docker run -d \
  --name augur-monitor \
  --env-file src/monitor/.env \
  -v $(pwd)/src/monitor/logs:/app/logs \
  augur-monitor
```

### Or use docker-compose:
Add to your `docker-compose.yml`:

```yaml
monitor:
  build: ./src/monitor
  env_file:
    - src/monitor/.env
  volumes:
    - ./src/monitor/logs:/app/logs
  restart: unless-stopped
  depends_on:
    - api
```

## Running Locally

1. Install dependencies:
```bash
pip install -r src/monitor/requirements.txt
```

2. Set environment variables (or use `.env` file with python-dotenv)

3. Run:
```bash
python src/monitor/monitor.py
```

## Logs

The monitor logs to both stdout and `/app/logs/monitor.log` file. When running in Docker, logs are also available via `docker logs augur-monitor`.

## Troubleshooting

### Container stops immediately

If the container stops immediately, check the logs:

```bash
docker logs augur-monitor
```

Common issues:
1. **Missing environment variables**: Check that all required variables are set in your `.env` file
2. **Configuration errors**: The monitor will log configuration errors on startup
3. **Keycloak authentication failure (401 Unauthorized)**:
   - **For password grant**: 
     - Ensure "Direct Access Grants" is enabled in Keycloak client settings
     - If the client is "confidential", you must also provide `KEYCLOAK_CLIENT_SECRET`
     - Verify username and password are correct
   - **For client credentials**: 
     - Verify `KEYCLOAK_CLIENT_ID` and `KEYCLOAK_CLIENT_SECRET` are correct
     - Ensure the client is configured to allow client credentials grant
4. **API connection issues**: Ensure the API_URL is correct and accessible

### Check container status

```bash
docker ps -a | grep augur-monitor
```

### Run interactively for debugging

```bash
docker run -it --rm --env-file src/monitor/.env augur-monitor
```

This will show all output directly and help identify startup issues.

## Email Alerts

When a threshold is exceeded, an email alert is sent with:
- Alert type (CPU, Memory, or Disk)
- Current values
- Threshold values
- System status summary

Emails are rate-limited per alert type (12 hours by default) to prevent spam.
