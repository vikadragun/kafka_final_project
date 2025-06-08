import json
import time
from confluent_kafka import Producer
import random

class ShopAPI:
    def __init__(self, kafka_config):
        self.producer = Producer(kafka_config)
        self.products = self._load_products()
        
    def _load_products(self):
        with open('products.json', 'r') as f:
            return json.load(f)
    
    def delivery_report(self, err, msg):
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')
    
    def send_products(self):
        for product in self.products:
            # Добавляем случайное изменение цены и количества для демонстрации
            modified_product = product.copy()
            modified_product['price']['amount'] = round(
                product['price']['amount'] * random.uniform(0.9, 1.1), 2)
            modified_product['stock']['available'] = random.randint(
                0, product['stock']['available'] * 2)
            
            self.producer.produce(
                'products',
                key=modified_product['product_id'],
                value=json.dumps(modified_product),
                callback=self.delivery_report
            )
            self.producer.flush()
            time.sleep(0.5)  # Задержка для имитации реального потока

if __name__ == '__main__':
    config = {
        'bootstrap.servers': 'kafka1:9093,kafka2:9094',
        'security.protocol': 'SSL',
        'ssl.ca.location': '/etc/kafka/secrets/ca-cert',
        'ssl.certificate.location': '/etc/kafka/secrets/kafka-cert',
        'ssl.key.location': '/etc/kafka/secrets/kafka-key',
        'acks': 'all'
    }
    
    api = ShopAPI(config)
    while True:
        api.send_products()
        time.sleep(60)  # Отправляем обновления каждую минуту
