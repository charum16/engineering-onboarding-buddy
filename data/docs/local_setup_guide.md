# Local Setup Guide

## Prerequisites
Install these before you start: Docker Desktop 4.x, Python 3.11, Node.js 20 LTS, Go 1.22 and GNU Make. Docker Desktop needs at least 8 GB of RAM allocated, otherwise `make up` fails with out-of-memory errors.

## Step by step
1. Make sure IT has added you to the GitHub organisation `meridian-labs`. This normally happens on day one.
2. Clone the monorepo: `git clone git@github.com:meridian-labs/meridian-platform.git`
3. Copy the environment template: `cp .env.example .env`
4. Run `make bootstrap`. It installs all dependencies and takes about 10 minutes.
5. Run `make up` to start every service with Docker Compose.
6. Check that the gateway is alive: `curl http://localhost:8080/healthz` should return `{"status":"ok"}`.
7. Run `make seed` to load sample data, then `make test` to run the unit tests.

## Example .env for local development
The values below are placeholders from the AWS documentation. Never commit real credentials. Real secrets live in AWS Secrets Manager.

```
DATABASE_URL=postgresql://dev:dev@localhost:5432/meridian
KAFKA_BROKERS=localhost:9092
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

## Troubleshooting
- Port 5432 already in use: stop any PostgreSQL you installed locally, then run `make up` again.
- `make bootstrap` fails with pip timeouts: connect to the company VPN (GlobalConnect) and retry.
- A service keeps restarting: run `make logs SERVICE=<name>` and read the last 50 lines.
