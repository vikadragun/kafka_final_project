#Структура проекта:

marketplace/
├── docker-compose.yml
├── README.md
├── shop_api/
│   ├── app.py
│   ├── products.json
│   ├── Dockerfile
│   └── requirements.txt
├── client_api/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── faust_stream/
│   ├── app.py
│   ├── banned_products.json
│   ├── Dockerfile
│   └── requirements.txt
├── spark_processing/
│   ├── Dockerfile
│   ├── recommendations.py
│   └── requirements.txt
├── kafka_config/
│   ├── server.properties
│   ├── client.properties
│   └── acl_commands.txt
├── prometheus/
│   ├── prometheus.yml
│   └── alerts.yml
├── grafana/
│   └── dashboards/
│       ├── kafka_dashboard.json
│       └── spark_dashboard.json
└── scripts/
    ├── init_kafka.sh
    └── hdfs_upload.sh
    
# Marketplace Processing System

Система обработки товаров для маркетплейса с аналитикой и рекомендациями.

## Технологии

- **Apache Kafka** (с TLS и ACL) - потоковая передача данных
- **Python** (Faust, CLI) - обработка потоков и API
- **Spark** (Scala) - аналитика и рекомендации
- **HDFS** - хранилище данных
- **Prometheus + Grafana** - мониторинг
- **Elasticsearch** - поиск товаров

## Запуск системы

1. Сгенерируйте SSL сертификаты:

chmod +x ./scripts/generate_ssl.sh  # Даем права на выполнение
./scripts/generate_ssl.sh           # Запускаем скрипт

После выполнения в папке ./kafka_secrets появятся:

- ca-cert — корневой сертификат.
- kafka-cert и kafka-key — клиентские сертификаты для Python-приложений.
- kafka.server.truststore.jks — хранилище доверенных сертификатов для брокеров.

2. Запустите систему:

docker-compose up -d

## Использование

###Отправка товаров

Shop API автоматически отправляет товары из файла shop_api/products.json в Kafka.

- Поиск товаров docker-compose exec client_api python app.py search "умные часы"

- Управление запрещенными товарами:

docker-compose exec faust_stream python app.py ban
docker-compose exec faust_stream python app.py unban
docker-compose exec faust_stream python app.py list_banned

##Мониторинг

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Kibana: http://localhost:5601

##Архитектура

- Shop API отправляет товары в топик Kafka products
- Faust App фильтрует запрещенные товары и отправляет разрешенные в filtered_products
- Spark читает из filtered_products, сохраняет в HDFS и генерирует рекомендации
- Client API позволяет искать товары и получать рекомендации
- Все запросы клиентов логируются в Elasticsearch и Kafka для аналитики
