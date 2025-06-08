from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, TrainValidationSplit
import json

def main():
    spark = SparkSession.builder \
        .appName("MarketplaceRecommendations") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.0") \
        .getOrCreate()
    
    # Чтение данных из Kafka
    products_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka1:9093,kafka2:9094") \
        .option("subscribe", "filtered_products") \
        .option("startingOffsets", "earliest") \
        .option("kafka.security.protocol", "SSL") \
        .option("kafka.ssl.truststore.location", "/etc/kafka/secrets/kafka.client.truststore.jks") \
        .option("kafka.ssl.truststore.password", "confluent") \
        .option("kafka.ssl.keystore.location", "/etc/kafka/secrets/kafka.client.keystore.jks") \
        .option("kafka.ssl.keystore.password", "confluent") \
        .load() \
        .selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), """
            product_id STRING, 
            name STRING, 
            description STRING,
            price STRUCT<amount: DOUBLE, currency: STRING>,
            category STRING,
            brand STRING,
            stock STRUCT<available: INT, reserved: INT>,
            tags ARRAY<STRING>,
            created_at TIMESTAMP
        """).alias("data")) \
        .select("data.*")
    
    requests_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka1:9093,kafka2:9094") \
        .option("subscribe", "client_requests") \
        .option("startingOffsets", "earliest") \
        .option("kafka.security.protocol", "SSL") \
        .load() \
        .selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), """
            type STRING,
            query STRING,
            user_id STRING,
            product_id STRING,
            timestamp TIMESTAMP
        """).alias("data")) \
        .select("data.*")
    
    # Сохранение в HDFS
    def write_to_hdfs(batch_df, batch_id):
        batch_df.write \
            .mode("append") \
            .parquet("hdfs://namenode:9000/data/products")
    
    products_query = products_df.writeStream \
        .foreachBatch(write_to_hdfs) \
        .outputMode("append") \
        .start()
    
    # Модель рекомендаций
    interactions = requests_df.filter(col("type") == "view") \
        .select(col("user_id").cast("integer"), 
                col("product_id").cast("integer"), 
                lit(1.0).alias("rating"))
    
    als = ALS(
        userCol="user_id",
        itemCol="product_id",
        ratingCol="rating",
        coldStartStrategy="drop",
        nonnegative=True
    )
    
    param_grid = ParamGridBuilder() \
        .addGrid(als.rank, [10, 50]) \
        .addGrid(als.maxIter, [5, 10]) \
        .addGrid(als.regParam, [0.01, 0.1]) \
        .build()
    
    evaluator = RegressionEvaluator(
        metricName="rmse",
        labelCol="rating",
        predictionCol="prediction")
    
    tv = TrainValidationSplit(
        estimator=als,
        estimatorParamMaps=param_grid,
        evaluator=evaluator,
        trainRatio=0.8)
    
    model = tv.fit(interactions)
    best_model = model.bestModel
    
    # Генерация рекомендаций
    user_recs = best_model.recommendForAllUsers(5)
    
    def send_recommendations(batch_df, batch_id):
        for row in batch_df.collect():
            user_id = row["user_id"]
            recommendations = [{
                "product_id": rec.product_id,
                "rating": rec.rating
            } for rec in row["recommendations"]]
            
            # Здесь можно добавить логику для отправки в Kafka
            print(f"Recommendations for user {user_id}: {recommendations}")
    
    recommendations_query = user_recs.writeStream \
        .foreachBatch(send_recommendations) \
        .outputMode("complete") \
        .start()
    
    products_query.awaitTermination()
    recommendations_query.awaitTermination()

if __name__ == "__main__":
    main()
