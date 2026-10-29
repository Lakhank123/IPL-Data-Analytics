"""Content Beyond Syllabus (CBS) Verification Engine.

Performs empirical, reproducible demonstrations of core Delta Lake
Lakehouse capabilities:
1. ACID Transaction Commit Log Parsing (_delta_log JSON)
2. Strict Schema Enforcement (Rejecting invalid schemas)
3. Controlled Schema Evolution (Dynamic column addition via mergeSchema)
4. Time Travel (Querying historical snapshot versions)

Course: Big Data Computing (BDC)
Institute: VESIT, Autonomous
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Automatic environment configuration for Windows runtime
if sys.platform == 'win32':
    if not os.environ.get('HADOOP_HOME') and os.path.exists(r'C:\Users\HP\hadoop'):
        os.environ['HADOOP_HOME'] = r'C:\Users\HP\hadoop'
        os.environ['PATH'] = r'C:\Users\HP\hadoop\bin;' + os.environ.get('PATH', '')
    if not os.environ.get('JAVA_HOME') and os.path.exists(r'C:\Program Files\Android\Android Studio\jbr'):
        os.environ['JAVA_HOME'] = r'C:\Program Files\Android\Android Studio\jbr'
    if not os.environ.get('PYSPARK_PYTHON'):
        short_python = r'C:\Users\HP\OneDrive\Desktop\IPLDAT~1\IPLDAT~1\VENV~1\Scripts\python.exe'
        os.environ['PYSPARK_PYTHON'] = short_python if os.path.exists(short_python) else sys.executable
    if not os.environ.get('PYSPARK_DRIVER_PYTHON'):
        os.environ['PYSPARK_DRIVER_PYTHON'] = os.environ['PYSPARK_PYTHON']

from pyspark.sql import SparkSession, functions as F
from delta import configure_spark_with_delta_pip


def main():
    print("=" * 75)
    print("CONTENT BEYOND SYLLABUS (CBS) VERIFICATION SUITE: DELTA LAKE & LAKEHOUSE")
    print("=" * 75)
    
    builder = (
        SparkSession.builder
        .master("local[*]")
        .appName("Delta-Lake-CBS-Verification")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "4")
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    
    test_table_dir = ROOT / 'data' / 'lakehouse' / 'cbs_demo_table'
    results = {}
    
    try:
        # =====================================================================
        # TEST 1: ACID TRANSACTION COMMIT LOG & ATOMICITY
        # =====================================================================
        print("\n--- TEST 1: VERIFYING ACID TRANSACTION COMMIT LOG ---")
        # Step 1A: Create initial table Version 0
        raw_m = spark.read.option("header", True).csv(str(ROOT / 'data' / 'raw' / 'matches.csv'))
        v0_data = raw_m.limit(5).select("match_id", "season", "team1", "team2", "winner")
        v0_data.write.format("delta").mode("overwrite").save(str(test_table_dir))
        
        delta_log_dir = test_table_dir / '_delta_log'
        v0_json = delta_log_dir / '00000000000000000000.json'
        
        if v0_json.exists():
            log_lines = [json.loads(line) for line in v0_json.read_text(encoding='utf-8').strip().split('\n')]
            commit_info = next((item['commitInfo'] for item in log_lines if 'commitInfo' in item), {})
            print(f"Commit Log 0 Found: {v0_json.name}")
            print(f"Timestamp: {commit_info.get('timestamp')}")
            print(f"Operation: {commit_info.get('operation')}")
            print(f"Engine Info: {commit_info.get('engineInfo')}")
            results['TEST_1_ACID_COMMIT'] = "PASSED"
        else:
            print("FAILED: Commit JSON not found!")
            results['TEST_1_ACID_COMMIT'] = "FAILED"

        # =====================================================================
        # TEST 2: SCHEMA ENFORCEMENT (REJECTION OF ILLEGAL COLUMNS)
        # =====================================================================
        print("\n--- TEST 2: VERIFYING SCHEMA ENFORCEMENT ---")
        # Attempt to append a record with an unexpected/corrupted column
        illegal_df = (
            raw_m.limit(2)
            .select("match_id", "season", "team1", "team2", "winner")
            .withColumn("corrupted_unauthorized_sensor", F.lit("ILLEGAL_VALUE_999"))
        )
        
        schema_blocked = False
        try:
            # Without mergeSchema option, Delta must strictly reject this write
            illegal_df.write.format("delta").mode("append").save(str(test_table_dir))
        except Exception as err:
            schema_blocked = True
            print("Delta Lake successfully caught and rejected schema violation!")
            print(f"Caught Expected Exception: {type(err).__name__}")
            
        if schema_blocked:
            results['TEST_2_SCHEMA_ENFORCEMENT'] = "PASSED"
        else:
            print("FAILED: Bad data was permitted to append!")
            results['TEST_2_SCHEMA_ENFORCEMENT'] = "FAILED"

        # =====================================================================
        # TEST 3: CONTROLLED SCHEMA EVOLUTION (mergeSchema = true)
        # =====================================================================
        print("\n--- TEST 3: VERIFYING CONTROLLED SCHEMA EVOLUTION ---")
        # Now append with an authorized legitimate new feature: 'tournament_stage'
        evolution_df = (
            raw_m.limit(3)
            .select("match_id", "season", "team1", "team2", "winner")
            .withColumn("tournament_stage", F.lit("League Stage"))
        )
        
        evolution_df.write.format("delta").option("mergeSchema", "true").mode("append").save(str(test_table_dir))
        
        evolved_table = spark.read.format("delta").load(str(test_table_dir))
        has_new_column = "tournament_stage" in evolved_table.columns
        print(f"Evolved Columns: {evolved_table.columns}")
        print(f"New column 'tournament_stage' present: {has_new_column}")
        print(f"Total rows after evolution append: {evolved_table.count()}")
        
        if has_new_column and evolved_table.count() == 8:
            results['TEST_3_SCHEMA_EVOLUTION'] = "PASSED"
        else:
            results['TEST_3_SCHEMA_EVOLUTION'] = "FAILED"

        # =====================================================================
        # TEST 4: TIME TRAVEL (HISTORICAL SNAPSHOT RECOVERY)
        # =====================================================================
        print("\n--- TEST 4: VERIFYING DELTA LAKE TIME TRAVEL ---")
        # Query Version 0 (before schema evolution and before append)
        v0_read = spark.read.format("delta").option("versionAsOf", 0).load(str(test_table_dir))
        # Query Version 1 (latest version after evolution and append)
        v1_read = spark.read.format("delta").option("versionAsOf", 1).load(str(test_table_dir))
        
        v0_rows = v0_read.count()
        v1_rows = v1_read.count()
        v0_has_col = "tournament_stage" in v0_read.columns
        v1_has_col = "tournament_stage" in v1_read.columns
        
        print(f"Version 0 Row Count: {v0_rows} (Expected 5) | Has 'tournament_stage': {v0_has_col} (Expected False)")
        print(f"Version 1 Row Count: {v1_rows} (Expected 8) | Has 'tournament_stage': {v1_has_col} (Expected True)")
        
        if v0_rows == 5 and v1_rows == 8 and not v0_has_col and v1_has_col:
            print("Time Travel successfully verified exact historical state rollback!")
            results['TEST_4_TIME_TRAVEL'] = "PASSED"
        else:
            print("FAILED: Time travel state does not match expected snapshots!")
            results['TEST_4_TIME_TRAVEL'] = "FAILED"
            
    finally:
        # Clean up test table
        spark.stop()
        
    print("\n" + "=" * 75)
    print("CONTENT BEYOND SYLLABUS (CBS) VERIFICATION SUMMARY")
    print("=" * 75)
    for test_name, status in results.items():
        print(f"  {test_name:<30}: [{status}]")
    print("=" * 75)
    
    all_passed = all(status == "PASSED" for status in results.values())
    if all_passed:
        print("ALL CONTENT BEYOND SYLLABUS REQUIREMENTS 100% EMPIRICALLY VERIFIED!")
    else:
        print("ONE OR MORE CBS TESTS FAILED.")
    return results


if __name__ == '__main__':
    main()
