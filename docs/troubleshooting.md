## 🐛 Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   # Check if ports are available
   netstat -tulpn | grep :8088
   netstat -tulpn | grep :5432
   netstat -tulpn | grep :6379
   ```

2. **Database connection errors**
   ```bash
   # Check PostgreSQL logs
   docker compose logs superset-postgres

   # Test connection
   docker compose exec superset-postgres psql -U superset -d superset -c "\l"
   ```

3. **Redis connection errors**
   ```bash
   # Check Redis logs
   docker compose logs superset-redis

   # Test connection
   docker compose exec superset-redis redis-cli --no-auth-warning -a $REDIS_PASSWORD ping
   ```

4. **Superset web interface not loading**
   ```bash
   # Check Superset logs
   docker compose logs superset-app

   # Check health
   docker compose exec superset-app curl -f http://localhost:8088/health


### Health Checks

All services include health checks:
- PostgreSQL: Connection test
- Redis: Ping test
- Superset: HTTP health endpoint
- Celery: Process inspection

### Log Monitoring

Monitor these log files:
- `/app/superset_home/logs/gunicorn_access.log`
- `/app/superset_home/logs/gunicorn_error.log`
- `/app/superset_home/logs/celery_worker.log`
- `/app/superset_home/logs/celery_beat.log`
