#!/bin/bash

# Создание топиков
kafka-topics --bootstrap-server kafka1:9093 --command-config /etc/kafka/secrets/client.properties \
  --create --topic products --partitions 3 --replication-factor 2

kafka-topics --bootstrap-server kafka1:9093 --command-config /etc/kafka/secrets/client.properties \
  --create --topic client_requests --partitions 3 --replication-factor 2

kafka-topics --bootstrap-server kafka1:9093 --command-config /etc/kafka/secrets/client.properties \
  --create --topic recommendations --partitions 3 --replication-factor 2

kafka-topics --bootstrap-server kafka1:9093 --command-config /etc/kafka/secrets/client.properties \
  --create --topic filtered_products --partitions 3 --replication-factor 2

# Настройка ACL
while read cmd; do
  kafka-acls --bootstrap-server kafka1:9093 --command-config /etc/kafka/secrets/client.properties $cmd
done < /acl_commands.txt

echo "Kafka setup completed"
