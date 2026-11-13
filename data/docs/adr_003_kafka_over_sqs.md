# ADR 003: Use Kafka instead of SQS for the event bus

## Status
Accepted.

## Context
The ledger-service must process payment events in order for each account, and we need to replay events when a consumer has a bug or when a new service is added. Amazon SQS standard queues do not guarantee ordering, and SQS FIFO queues cannot replay events once they are consumed.

## Decision
We use Apache Kafka, run as AWS MSK, as the event bus. Events are partitioned by `account_id`, which guarantees ordering per account. The retention period is 7 days, which allows replay.

## Consequences
- Consumers must be idempotent, because events can be delivered more than once.
- Kafka costs more to run than SQS and needs more operational knowledge.
- New services can subscribe to existing topics without any change to the producers.
