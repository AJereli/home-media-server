# Nginx Configuration

## Overview
This nginx setup provides reverse proxy and subdomain routing for the home media server. It's configured to handle multiple subdomains with SSL termination and security headers.

## Configuration Structure
- `nginx.conf` - Main nginx configuration with optimized settings
- `conf.d/` - Individual subdomain configurations
- `ssl/` - SSL certificates storage
- `logs/` - Nginx access and error logs

## Current Subdomains
- `person.jereli-projects.de` - Placeholder page with inline HTML

## Scaling Instructions

### Adding New Subdomains
1. Create new config file in `conf.d/` directory:
   ```bash
   cp conf.d/person.jereli-projects.de.conf conf.d/newdomain.example.com.conf
   ```
2. Edit the new config file:
   - Update `server_name` directive
   - Configure upstream servers or static content
   - Update log file paths
3. Reload nginx:
   ```bash
   docker-compose -f docker-compose-nginx.yml exec nginx nginx -s reload
   ```

### SSL Certificate Setup
1. Place certificates in `ssl/` directory
2. Uncomment SSL configuration in subdomain configs
3. Update certificate paths in server blocks

### Load Balancing
For high traffic, add upstream blocks in subdomain configs:
```nginx
upstream backend {
    server app1:3000;
    server app2:3000;
    server app3:3000;
}
```

### Performance Tuning
- Adjust `worker_processes` in nginx.conf
- Increase `worker_connections` for high concurrency
- Configure rate limiting for protection

## Running
```bash
docker-compose -f docker-compose-nginx.yml up -d
```