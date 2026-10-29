"""Enterprise Data Lakehouse ETL using Apache Spark and Delta Lake.

Implements the full Medallion Architecture (Bronze -> Silver -> Gold)
for historical Indian Premier League (IPL) data processing.

Course: Big Data Computing (BDC)
Institute: VESIT, Autonomous
"""
import os
import sys
from pathlib import Path

# Resolve project root
ROOT = Path(__file__).resolve().parents[1]

# Automatic environment configuration for Windows runtime
if sys.platform == 'win32':
    if not os.environ.get('HADOOP_HOME') and os.path.exists(r'C:\Users\HP\hadoop'):
        os.environ['HADOOP_HOME'] = r'C:\Users\HP\hadoop'
        os.environ['PATH'] = r'C:\Users\HP\hadoop\bin;' + os.environ.get('PATH', '')
    if not os.environ.get('JAVA_HOME') and os.path.exists(r'C:\Program Files\Android\Android Studio\jbr'):
        os.environ['JAVA_HOME'] = r'C:\Program Files\Android\Android Studio\jbr'
    if not os.environ.get('PYSPARK_PYTHON'):
        # Prefer 8.3 short path if exists to avoid spaces in path
        short_python = r'C:\Users\HP\OneDrive\Desktop\IPLDAT~1\IPLDAT~1\VENV~1\Scripts\python.exe'
        os.environ['PYSPARK_PYTHON'] = short_python if os.path.exists(short_python) else sys.executable
    if not os.environ.get('PYSPARK_DRIVER_PYTHON'):
        os.environ['PYSPARK_DRIVER_PYTHON'] = os.environ['PYSPARK_PYTHON']

from pyspark.sql import SparkSession, functions as F
from delta import configure_spark_with_delta_pip


def create_lakehouse_session() -> SparkSession:
    """Initialize SparkSession with Delta Lake extensions and catalog."""
    builder = (
        SparkSession.builder
        .master("local[*]")
        .appName("IPL-Data-Lakehouse-Engine")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
        .config("spark.sql.debug.maxToStringFields", "200")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def run_pipeline():
    raw_dir = ROOT / 'data' / 'raw'
    lakehouse_dir = ROOT / 'data' / 'lakehouse'
    
    if not (raw_dir / 'matches.csv').exists() or not (raw_dir / 'deliveries.csv').exists():
        raise FileNotFoundError(
            "Raw datasets not found. Ingest first with: python -m src.ingestion"
        )
        
    spark = create_lakehouse_session()
    print("=" * 70)
    print("STARTING IPL DATA LAKEHOUSE MEDALLION PIPELINE (APACHE SPARK + DELTA LAKE)")
    print(f"Spark Version: {spark.version}")
    print("=" * 70)
    
    try:
        # =====================================================================
        # 1. BRONZE LAYER: Raw Data Ingestion with Ingestion Metadata
        # =====================================================================
        print("\n>>> STAGE 1: INGESTING RAW DATA INTO BRONZE DELTA TABLES...")
        raw_matches = (
            spark.read.option("header", True)
            .option("inferSchema", True)
            .csv(str(raw_dir / 'matches.csv'))
            .withColumn("ingestion_timestamp", F.current_timestamp())
            .withColumn("source_archive", F.lit("Cricsheet-IPL-JSON"))
        )
        
        raw_deliveries = (
            spark.read.option("header", True)
            .option("inferSchema", True)
            .csv(str(raw_dir / 'deliveries.csv'))
            .withColumn("ingestion_timestamp", F.current_timestamp())
            .withColumn("source_archive", F.lit("Cricsheet-IPL-JSON"))
        )
        
        bronze_matches_path = str(lakehouse_dir / 'bronze' / 'matches')
        bronze_deliveries_path = str(lakehouse_dir / 'bronze' / 'deliveries')
        
        raw_matches.write.format("delta").mode("overwrite").save(bronze_matches_path)
        raw_deliveries.write.format("delta").mode("overwrite").save(bronze_deliveries_path)
        
        m_count = spark.read.format("delta").load(bronze_matches_path).count()
        d_count = spark.read.format("delta").load(bronze_deliveries_path).count()
        print(f"Bronze Layer Written: {m_count:,} matches | {d_count:,} deliveries")
        
        # =====================================================================
        # 2. SILVER LAYER: Cleaning, Validation, Enrichment, and Partitioning
        # =====================================================================
        print("\n>>> STAGE 2: TRANSFORMING & ENRICHING DATA INTO SILVER DELTA TABLES...")
        b_matches = spark.read.format("delta").load(bronze_matches_path)
        b_deliveries = spark.read.format("delta").load(bronze_deliveries_path)
        
        # Deduplication & Type standardisation
        clean_matches = (
            b_matches
            .withColumn("match_id", F.col("match_id").cast("string"))
            .withColumn("season", F.col("season").cast("string"))
            .dropDuplicates(["match_id"])
            .filter(F.col("match_id").isNotNull())
        )
        
        # Delivery cleaning, metrics calculation, and enrichment
        enriched_deliveries = (
            b_deliveries
            .withColumn("match_id", F.col("match_id").cast("string"))
            .filter(F.col("match_id").isNotNull() & F.col("total_runs").isNotNull())
            .withColumn("batter_runs", F.col("batter_runs").cast("integer"))
            .withColumn("extras", F.col("extras").cast("integer"))
            .withColumn("total_runs", F.col("total_runs").cast("integer"))
            .withColumn("wides", F.coalesce(F.col("wides").cast("integer"), F.lit(0)))
            .withColumn("noballs", F.coalesce(F.col("noballs").cast("integer"), F.lit(0)))
            .withColumn("byes", F.coalesce(F.col("byes").cast("integer"), F.lit(0)))
            .withColumn("legbyes", F.coalesce(F.col("legbyes").cast("integer"), F.lit(0)))
            .withColumn("is_boundary_non_boundary", F.coalesce(F.col("is_boundary_non_boundary").cast("integer"), F.lit(0)))
            # Cricket Analytical Flags
            .withColumn("is_four", F.when((F.col("batter_runs") == 4) & (F.col("is_boundary_non_boundary") == 0), 1).otherwise(0))
            .withColumn("is_six", F.when((F.col("batter_runs") == 6) & (F.col("is_boundary_non_boundary") == 0), 1).otherwise(0))
            .withColumn("legal_ball", F.when((F.col("wides") == 0) & (F.col("noballs") == 0), 1).otherwise(0))
            .withColumn("batter_ball", F.when(F.col("wides") == 0, 1).otherwise(0))
            .withColumn("bowler_runs", F.col("batter_runs") + F.col("wides") + F.col("noballs"))
            .withColumn(
                "bowler_wicket",
                F.when(
                    F.col("dismissal_kind").isin(
                        ["bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"]
                    ),
                    1
                ).otherwise(0)
            )
        )
        
        # Inner join to attach match dimensions to delivery events
        joined_deliveries = enriched_deliveries.join(
            clean_matches.select("match_id", "season", "date", "venue"),
            on="match_id",
            how="inner"
        )
        
        silver_matches_path = str(lakehouse_dir / 'silver' / 'matches')
        silver_deliveries_path = str(lakehouse_dir / 'silver' / 'deliveries')
        
        clean_matches.write.format("delta").mode("overwrite").save(silver_matches_path)
        joined_deliveries.write.format("delta").partitionBy("season").mode("overwrite").save(silver_deliveries_path)
        
        # Populate legacy Parquet directories for backward compatibility
        clean_matches.write.mode("overwrite").parquet(str(ROOT / 'data' / 'silver' / 'matches'))
        joined_deliveries.write.mode("overwrite").partitionBy("season").parquet(str(ROOT / 'data' / 'silver' / 'deliveries'))
        
        print("Silver Layer Written with Delta Lake ACID guarantees (deliveries partitioned by season).")
        
        # =====================================================================
        # 3. GOLD LAYER: Aggregated Analytical Lakehouse Datasets
        # =====================================================================
        print("\n>>> STAGE 3: COMPUTING GOLD ANALYTICAL MARTS USING SPARK SQL...")
        
        silver_deliveries = spark.read.format("delta").load(silver_deliveries_path)
        silver_matches = spark.read.format("delta").load(silver_matches_path)
        
        silver_deliveries.createOrReplaceTempView("deliveries")
        silver_matches.createOrReplaceTempView("matches")
        
        # Mart 1: Season Summary
        gold_season_summary = spark.sql("""
            SELECT 
                season,
                COUNT(DISTINCT match_id) AS matches,
                COUNT(*) AS delivery_events,
                SUM(total_runs) AS total_runs,
                SUM(is_six) AS sixes,
                SUM(is_four) AS fours,
                SUM(bowler_wicket) AS wickets
            FROM deliveries
            GROUP BY season
            ORDER BY season
        """)
        
        # Mart 2: Batting Leaderboard
        gold_batting = spark.sql("""
            SELECT 
                season,
                batter,
                SUM(batter_runs) AS runs,
                SUM(batter_ball) AS balls_faced,
                SUM(is_four) AS fours,
                SUM(is_six) AS sixes,
                CASE 
                    WHEN SUM(batter_ball) > 0 
                    THEN ROUND(SUM(batter_runs) * 100.0 / SUM(batter_ball), 2)
                    ELSE 0.0 
                END AS strike_rate
            FROM deliveries
            GROUP BY season, batter
        """)
        
        # Mart 3: Bowling Leaderboard
        gold_bowling = spark.sql("""
            SELECT 
                season,
                bowler,
                SUM(bowler_wicket) AS wickets,
                SUM(bowler_runs) AS runs_conceded,
                SUM(legal_ball) AS legal_deliveries,
                CASE 
                    WHEN SUM(legal_ball) > 0 
                    THEN ROUND(SUM(bowler_runs) * 6.0 / SUM(legal_ball), 2)
                    ELSE 0.0 
                END AS economy_rate
            FROM deliveries
            GROUP BY season, bowler
        """)
        
        # Mart 4: Venue Insights (First Innings Scoring)
        gold_venues = spark.sql("""
            WITH first_innings AS (
                SELECT 
                    season,
                    venue,
                    match_id,
                    SUM(total_runs) AS match_first_innings_runs
                FROM deliveries
                WHERE innings = 1
                GROUP BY season, venue, match_id
            )
            SELECT 
                season,
                venue,
                COUNT(DISTINCT match_id) AS innings_count,
                SUM(match_first_innings_runs) AS total_first_innings_runs,
                ROUND(AVG(match_first_innings_runs), 1) AS avg_first_innings_score
            FROM first_innings
            GROUP BY season, venue
        """)
        
        # Mart 5: Team Performance Summary
        gold_teams = spark.sql("""
            WITH match_teams AS (
                SELECT team1 AS team, winner, match_id, toss_winner FROM matches
                UNION ALL
                SELECT team2 AS team, winner, match_id, toss_winner FROM matches
            )
            SELECT 
                team,
                COUNT(DISTINCT match_id) AS matches_played,
                SUM(CASE WHEN winner = team THEN 1 ELSE 0 END) AS wins,
                ROUND(SUM(CASE WHEN winner = team THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT match_id), 2) AS win_percentage,
                SUM(CASE WHEN toss_winner = team THEN 1 ELSE 0 END) AS toss_wins
            FROM match_teams
            WHERE team IS NOT NULL AND team != ''
            GROUP BY team
            ORDER BY wins DESC
        """)
        
        # Persist Gold tables in Delta format
        gold_dir = lakehouse_dir / 'gold'
        gold_season_summary.write.format("delta").mode("overwrite").save(str(gold_dir / 'season_summary'))
        gold_batting.write.format("delta").mode("overwrite").save(str(gold_dir / 'batting'))
        gold_bowling.write.format("delta").mode("overwrite").save(str(gold_dir / 'bowling'))
        gold_venues.write.format("delta").mode("overwrite").save(str(gold_dir / 'venues'))
        gold_teams.write.format("delta").mode("overwrite").save(str(gold_dir / 'teams'))
        
        # Populate legacy Parquet directories for backward compatibility
        gold_season_summary.write.mode("overwrite").parquet(str(ROOT / 'data' / 'gold' / 'season_summary'))
        gold_batting.write.mode("overwrite").parquet(str(ROOT / 'data' / 'gold' / 'batting'))
        
        print("Gold Lakehouse Layer Created with 5 Dedicated Analytical Marts.")
        print("\n>>> SAMPLE GOLD OUTPUT: SEASON SUMMARY (LAKEHOUSE DELTA)")
        gold_season_summary.show(10, truncate=False)
        
        print("=" * 70)
        print("IPL DATA LAKEHOUSE PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"Bronze Delta Tables: {lakehouse_dir / 'bronze'}")
        print(f"Silver Delta Tables: {lakehouse_dir / 'silver'}")
        print(f"Gold Delta Tables:   {lakehouse_dir / 'gold'}")
        print("=" * 70)
        
    finally:
        spark.stop()


if __name__ == '__main__':
    run_pipeline()
