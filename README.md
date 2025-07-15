# AWS Security Group Manager

A containerized Python application that automatically manages dynamic access to AWS Security Groups based on your current public IP address.

## Description

This project solves the problem of dynamic access to AWS resources when your public IP changes frequently. The application automatically detects IP changes and updates AWS Security Group rules accordingly, while optimizing API calls to avoid unnecessary operations.

## Features

**Smart IP Management**: Automatically detects IP changes and updates Security Group rules
**Optimized AWS Calls**: Avoids unnecessary API calls when IP hasn't changed
**Periodic Verification**: Configurable forced checks to prevent configuration drift
**Persistent Data**: Saves current IP and last update timestamps
**Continuous Execution**: Runs as a daemon with configurable cron scheduling
**Syslog Support**: Optional logging to external syslog servers

## Project Structure

```
aws-security-group-updated/
├── data/                    # Persistent data volume
│   ├── current_ip.txt      # Current saved IP
│   └── last_update.txt     # Last security group update timestamp
├── src/
│   ├── main.py             # Main application
│   ├── entrypoint.sh       # Container startup script
│   ├── cron-job.sh         # Cron job wrapper
│   ├── cron-wrapper.sh     # Environment variables wrapper (auto-generated)
│   ├── Dockerfile          # Container configuration
│   ├── docker-compose.yml  # Docker orchestration
│   ├── requirements.txt    # Python dependencies
│   └── .env               # Environment variables (create this)
└── README.md
```

## Configuration

### Create `.env` file in `src/` directory

```bash
# AWS Security Group configuration
SECURITY_GROUP_ID=sg-xxxxxxxxxx
PORT=22
PROTOCOL=tcp
RULE_DESCRIPTION=Dynamic IP access

# Force check interval (hours)
FORCE_CHECK_HOURS=24

# AWS credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=eu-west-1

# Optional syslog configuration
SYSLOG_SERVER=your.syslog.server
SYSLOG_PORT=514
```

### AWS Permissions

Ensure your AWS credentials have the following permissions:
- `ec2:DescribeSecurityGroups`
- `ec2:AuthorizeSecurityGroupIngress`
- `ec2:RevokeSecurityGroupIngress`

## Usage

### Start the application
```bash
cd src
docker-compose up -d --build
```

### View logs
```bash
docker-compose logs -f
```

### Stop the application
```bash
docker-compose down
```

### Manual IP check (without interrupting cron)
```bash
docker-compose exec sg-manager /usr/local/bin/python3 /app/main.py
```

## How it Works

1. **IP Detection**: Contacts `https://api.ipify.org` to get current public IP
2. **Change Detection**: Compares with previously saved IP
3. **Time-based Verification**: Checks if forced verification is needed based on configured interval
4. **AWS Optimization**: Skips AWS API calls if IP unchanged and no forced check needed
5. **Rule Management**: Adds new IP and removes old IP from Security Group when necessary
6. **Data Persistence**: Saves current IP and update timestamp for future checks

## Dependencies

- Python 3.11
- boto3: AWS SDK for Python
- requests: HTTP library for IP detection

## Configuration Options

### Execution Frequency
Modify `CRON_SCHEDULE` in `docker-compose.yml`:
```yaml
- CRON_SCHEDULE=*/10 * * * *  # Every 10 minutes
```

### Force Check Interval
```yaml
- FORCE_CHECK_HOURS=12  # Force check every 12 hours
```

### Syslog Logging
Uncomment and configure in `docker-compose.yml`:
```yaml
- SYSLOG_SERVER=your.syslog.server
- SYSLOG_PORT=514
```

## Notes

- IPs are saved as CIDR `/32` (single address)
- Rule descriptions are configurable via environment variables
- Timestamps are stored in ISO format for cross-platform compatibility
- Forced checks prevent configuration drift
- All logging outputs to both console and optionally to syslog