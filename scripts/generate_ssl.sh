#!/bin/bash

set -e

# Создаем папку для сертификатов
mkdir -p ./kafka_secrets
cd ./kafka_secrets

# Генерируем Root CA (самоподписанный сертификат)
openssl req -new -x509 -keyout ca.key -out ca.crt -days 365 -subj "/CN=Marketplace Kafka CA" -passout pass:confluent
keytool -keystore kafka.client.truststore.jks -alias CARoot -import -file ca.crt -storepass confluent -noprompt
keytool -keystore kafka.server.truststore.jks -alias CARoot -import -file ca.crt -storepass confluent -noprompt

# Генерируем сертификаты для брокеров (kafka1, kafka2)
for broker in kafka1 kafka2; do
    # Генерируем ключ и CSR
    keytool -keystore kafka.$broker.keystore.jks -alias $broker -validity 365 -genkey -keyalg RSA -storepass confluent -keypass confluent -dname "CN=$broker"
    
    # Подписываем сертификат CA
    keytool -keystore kafka.$broker.keystore.jks -alias $broker -certreq -file $broker.csr -storepass confluent
    openssl x509 -req -CA ca.crt -CAkey ca.key -in $broker.csr -out $broker.crt -days 365 -CAcreateserial -passin pass:confluent
    
    # Импортируем CA и подписанный сертификат в keystore
    keytool -keystore kafka.$broker.keystore.jks -alias CARoot -import -file ca.crt -storepass confluent -noprompt
    keytool -keystore kafka.$broker.keystore.jks -alias $broker -import -file $broker.crt -storepass confluent -keypass confluent -noprompt
    
    # Создаем файлы для удобного использования в Python-клиентах
    keytool -importkeystore -srckeystore kafka.$broker.keystore.jks -destkeystore $broker.p12 -deststoretype PKCS12 -srcstorepass confluent -deststorepass confluent
    openssl pkcs12 -in $broker.p12 -out $broker.pem -passin pass:confluent -nodes
    openssl x509 -outform pem -in $broker.crt -out $broker.cert.pem
    
    # Удаляем временные файлы
    rm $broker.csr $broker.p12
done

# Генерируем клиентский сертификат (для Faust, Spark и других клиентов)
keytool -keystore kafka.client.keystore.jks -alias client -validity 365 -genkey -keyalg RSA -storepass confluent -keypass confluent -dname "CN=client"
keytool -keystore kafka.client.keystore.jks -alias client -certreq -file client.csr -storepass confluent
openssl x509 -req -CA ca.crt -CAkey ca.key -in client.csr -out client.crt -days 365 -CAcreateserial -passin pass:confluent
keytool -keystore kafka.client.keystore.jks -alias CARoot -import -file ca.crt -storepass confluent -noprompt
keytool -keystore kafka.client.keystore.jks -alias client -import -file client.crt -storepass confluent -keypass confluent -noprompt

# Создаем PEM-файлы для Python-клиентов
openssl pkcs12 -in kafka.client.keystore.jks -out client.pem -passin pass:confluent -nodes -nokeys
openssl pkcs12 -in kafka.client.keystore.jks -out client.key -passin pass:confluent -nodes -nocerts
cat client.crt > kafka-cert
cat client.key >> kafka-cert
mv ca.crt ca-cert
mv client.key kafka-key

# Чистим временные файлы
rm *.csr *.srl client.pem client.key client.crt

echo "SSL-сертификаты успешно сгенерированы в папке ./kafka_secrets"
