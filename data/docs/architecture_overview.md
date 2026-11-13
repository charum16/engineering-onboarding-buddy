# Architecture Overview

## System summary
Meridian Pay is our payments platform. It is made of eight services that live in one monorepo called `meridian-platform`. Services talk to each other synchronously over REST through the API gateway, and asynchronously through Kafka events. Everything runs on Kubernetes (AWS EKS) in the ap-south-1 (Mumbai) region.

## Request flow
A client request first reaches the api-gateway, which is built on Envoy. The gateway validates the JWT that auth-service issued. Authenticated requests are routed to billing-service or payments-gateway. The payments-gateway calls the external card network, then publishes a `payment.completed` event on Kafka. The ledger-service consumes that event and writes the double-entry ledger record. The notification-service consumes the same event and sends the customer a receipt.

## Data stores
- PostgreSQL 15: one database per service. A service must never read another service's database; use its API or events instead.
- Redis 7: caching and rate limiting.
- Amazon S3: storage for generated invoice PDFs.
- Kafka (AWS MSK): event bus with 7 days of retention.

## Environments
There are three environments. Dev runs locally with Docker Compose. Staging runs on the EKS cluster `meridian-stg` and deploys automatically on every merge to main. Production runs on `meridian-prod` and needs a manual approval before each deploy.

## Observability
Metrics are collected by Prometheus and shown in Grafana dashboards. Logs go to Loki. Alerts are routed through PagerDuty. Every service exposes a `/healthz` endpoint and a `/metrics` endpoint.

## Tech conventions
Python services use FastAPI. Go services use the chi router. TypeScript services use Express. The web-app is a React application written in TypeScript.
