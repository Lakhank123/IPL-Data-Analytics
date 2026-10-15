"""Spark ETL from Cricsheet-derived CSV to Silver and Gold Parquet."""
from pathlib import Path
from pyspark.sql import SparkSession, functions as F


def main():
    if not Path('data/raw/matches.csv').exists():
        raise FileNotFoundError('Run: python -m src.ingestion')
    spark = (SparkSession.builder.master('local[*]').appName('IPL-InsightX')
             .config('spark.sql.shuffle.partitions', '8').getOrCreate())
    try:
        matches = spark.read.option('header', True).option('inferSchema', True).csv('data/raw/matches.csv')
        balls = spark.read.option('header', True).option('inferSchema', True).csv('data/raw/deliveries.csv')
        matches = matches.withColumn('match_id', F.col('match_id').cast('string')).withColumn('season', F.col('season').cast('string'))
        balls = balls.withColumn('match_id', F.col('match_id').cast('string'))
        valid_matches = matches.dropDuplicates(['match_id']).filter(F.col('match_id').isNotNull())
        valid_balls = balls.filter(F.col('match_id').isNotNull() & F.col('total_runs').isNotNull())
        joined = valid_balls.join(valid_matches.select('match_id', 'season', 'date', 'venue'), 'match_id', 'inner')
        valid_matches.write.mode('overwrite').parquet('data/silver/matches')
        joined.write.mode('overwrite').partitionBy('season').parquet('data/silver/deliveries')
        season_summary = (joined.groupBy('season')
                          .agg(F.countDistinct('match_id').alias('matches'),
                               F.count('*').alias('delivery_events'),
                               F.sum('total_runs').alias('total_runs'),
                               F.sum(F.when((F.col('batter_runs') == 6) & (F.col('is_boundary_non_boundary') == 0), 1).otherwise(0)).alias('sixes'))
                          .orderBy('season'))
        batting = (joined.groupBy('season', 'batter')
                   .agg(F.sum('batter_runs').alias('runs'),
                        F.sum(F.when(F.col('wides') == 0, 1).otherwise(0)).alias('balls_faced'))
                   .withColumn('strike_rate', F.when(F.col('balls_faced') > 0, F.round(F.col('runs') * 100 / F.col('balls_faced'), 2))))
        season_summary.write.mode('overwrite').parquet('data/gold/season_summary')
        batting.write.mode('overwrite').parquet('data/gold/batting')
        print('Processed', valid_matches.count(), 'matches;', joined.count(), 'delivery events')
        season_summary.show(30, truncate=False)
    finally:
        spark.stop()

if __name__ == '__main__':
    main()
