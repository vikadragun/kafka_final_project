import json
from confluent_kafka import Producer, Consumer
import argparse
from elasticsearch import Elasticsearch

class ClientAPI:
    def __init__(self, kafka_config, es_config):
        self.producer = Producer(kafka_config)
        self.consumer = Consumer({
            **kafka_config,
            'group.id': 'client-api-group',
            'auto.offset.reset': 'earliest'
        })
        self.es = Elasticsearch([es_config])
        self.consumer.subscribe(['recommendations'])
    
    def search_product(self, query):
        # Поиск в Elasticsearch
        es_result = self.es.search(index='products', body={
            'query': {
                'multi_match': {
                    'query': query,
                    'fields': ['name^3', 'description', 'brand', 'category']
                }
            }
        })
        
        # Отправка запроса в Kafka для аналитики
        self.producer.produce(
            'client_requests',
            value=json.dumps({
                'type': 'search',
                'query': query,
                'results_count': len(es_result['hits']['hits'])
            })
        )
        self.producer.flush()
        
        return es_result['hits']['hits']
    
    def get_recommendations(self, user_id):
        # Отправка запроса в Kafka
        self.producer.produce(
            'client_requests',
            value=json.dumps({
                'type': 'recommendation_request',
                'user_id': user_id
            })
        )
        self.producer.flush()
        
        # Ожидание рекомендаций (таймаут 10 сек)
        recommendations = []
        start_time = time.time()
        while time.time() - start_time < 10:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
            
            data = json.loads(msg.value())
            if data.get('user_id') == user_id:
                recommendations = data.get('products', [])
                break
        
        return recommendations

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Client API for Marketplace')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Поиск товаров
    search_parser = subparsers.add_parser('search')
    search_parser.add_argument('query', help='Search query')
    
    # Получение рекомендаций
    rec_parser = subparsers.add_parser('recommend')
    rec_parser.add_argument('user_id', help='User ID for recommendations')
    
    args = parser.parse_args()
    
    kafka_config = {
        'bootstrap.servers': 'kafka1:9093,kafka2:9094',
        'security.protocol': 'SSL',
        'ssl.ca.location': '/etc/kafka/secrets/ca-cert',
        'ssl.certificate.location': '/etc/kafka/secrets/kafka-cert',
        'ssl.key.location': '/etc/kafka/secrets/kafka-key'
    }
    
    api = ClientAPI(kafka_config, es_config={'host': 'elasticsearch', 'port': 9200})
    
    if args.command == 'search':
        results = api.search_product(args.query)
        print(f"Found {len(results)} products:")
        for product in results:
            print(f"{product['_source']['name']} - {product['_source']['price']['amount']} {product['_source']['price']['currency']}")
    
    elif args.command == 'recommend':
        recs = api.get_recommendations(args.user_id)
        print(f"Recommendations for user {args.user_id}:")
        for product in recs:
            print(f"{product['name']} - {product['price']['amount']} {product['price']['currency']}")
