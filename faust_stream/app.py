import faust
import json
from typing import List, Dict

app = faust.App(
    'product-filter',
    broker='kafka://kafka1:9093,kafka2:9094',
    broker_credentials=faust.SSLContext(
        cafile='/etc/kafka/secrets/ca-cert',
        certfile='/etc/kafka/secrets/kafka-cert',
        keyfile='/etc/kafka/secrets/kafka-key',
    ),
    store='memory://',
    topic_partitions=3,
)

class Product(faust.Record):
    product_id: str
    name: str
    description: str
    price: Dict[str, str]
    category: str
    brand: str
    stock: Dict[str, int]
    sku: str
    tags: List[str]
    specifications: Dict[str, str]

products_topic = app.topic('products', value_type=Product)
filtered_topic = app.topic('filtered_products', value_type=Product)

banned_products = set()

def load_banned_products():
    try:
        with open('banned_products.json', 'r') as f:
            data = json.load(f)
            banned_products.update(data['banned_ids'])
    except FileNotFoundError:
        print("No banned products file found, starting with empty list")

@app.task
async def on_started():
    load_banned_products()

@app.agent(products_topic)
async def process_products(stream):
    async for product in stream:
        if product.product_id not in banned_products:
            await filtered_topic.send(value=product)
        else:
            print(f"Filtered banned product: {product.product_id} - {product.name}")

@app.command()
async def ban():
    """Add product to banned list"""
    product_id = input("Enter product ID to ban: ")
    banned_products.add(product_id)
    save_banned_products()
    print(f"Product {product_id} added to banned list")

@app.command()
async def unban():
    """Remove product from banned list"""
    product_id = input("Enter product ID to unban: ")
    if product_id in banned_products:
        banned_products.remove(product_id)
        save_banned_products()
        print(f"Product {product_id} removed from banned list")
    else:
        print(f"Product {product_id} not found in banned list")

@app.command()
async def list_banned():
    """List all banned products"""
    print("Banned product IDs:")
    for product_id in banned_products:
        print(f"- {product_id}")

def save_banned_products():
    with open('banned_products.json', 'w') as f:
        json.dump({'banned_ids': list(banned_products)}, f)

if __name__ == '__main__':
    app.main()
