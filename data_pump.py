import oracledb
import pyodbc
import pandas as pd
import json
import argparse
import sys
import os
import struct

# --- CONFIGURATION ---
ORACLE_CONFIG = {
    "user": "ERIC_DEV",
    "password": "Eric_Project_123",
    "dsn": "127.0.0.1:1521/xepdb1"
}

FABRIC_CONFIG = {
    "server": "6rlqav7popeedpf3bdns7qk4fm-bypqfuwvnu4efnp5hxcw2ptic4.datawarehouse.fabric.microsoft.com",
    "database": "Fabric_Destination",
    "username": "ericgriffin.wiseline@rackspace.com"
}

# --- BATCH SETTINGS ---
CHUNK_SIZE = 10000  # Number of rows to process at a time

def move_data_to_fabric(dry_run=False):
    token = os.environ.get("FABRIC_ACCESS_TOKEN")
    mode_label = "[DRY RUN]" if dry_run else "[LIVE]"
    auth_label = "TOKEN-BASED" if token else "INTERACTIVE"
    
    print(f"\n🚰 {mode_label} Initializing Data Pump ({auth_label})")
    
    # 1. Load Sequence
    try:
        with open("migration_sequence.json", "r") as f:
            sequence = json.load(f)
    except FileNotFoundError:
        print("❌ Error: migration_sequence.json not found. Run the orchestrator first.")
        return

    # 2. Fabric Connection Setup
    try:
        if token:
            f_conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={FABRIC_CONFIG['server']};"
                f"DATABASE={FABRIC_CONFIG['database']};"
                f"Encrypt=yes;"
                f"TrustServerCertificate=no;"
            )
            token_bytes = token.encode("utf-16-le")
            token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
            f_conn = pyodbc.connect(f_conn_str, attrs_before={1256: token_struct})
        else:
            f_conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={FABRIC_CONFIG['server']};"
                f"DATABASE={FABRIC_CONFIG['database']};"
                f"UID={FABRIC_CONFIG['username']};"
                f"Authentication=ActiveDirectoryInteractive;"
                f"Encrypt=yes;"
                f"TrustServerCertificate=no;"
            )
            f_conn = pyodbc.connect(f_conn_str)

        f_cursor = f_conn.cursor()
        f_cursor.fast_executemany = True
        print("🔗 Fabric Connection Verified.")

        # 3. Migration Loop
        for table in sequence:
            print(f"   ∟ Processing: {table}...", end=" ", flush=True)

            # A. Connect to Oracle
            o_conn = oracledb.connect(
                user=ORACLE_CONFIG["user"], 
                password=ORACLE_CONFIG["password"], 
                dsn=ORACLE_CONFIG["dsn"]
            )
            
            query = f"SELECT * FROM {table}"
            if dry_run:
                query = f"SELECT * FROM {table} FETCH FIRST 5 ROWS ONLY"
            
            total_rows_migrated = 0
            
            # Use chunksize to stream data from Oracle rather than loading all at once
            # This is the "Safety Valve" for huge datasets
            for df_chunk in pd.read_sql(query, o_conn, chunksize=CHUNK_SIZE):
                if df_chunk.empty:
                    continue

                if dry_run:
                    print(f"✅ [MOCK] Verified {len(df_chunk)} sample rows.")
                    total_rows_migrated += len(df_chunk)
                    break # Only process one chunk in dry run
                else:
                    # B. Push Chunk to Fabric
                    placeholders = ", ".join(["?"] * len(df_chunk.columns))
                    columns = ", ".join(df_chunk.columns)
                    insert_sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                    
                    data_tuples = [tuple(x) for x in df_chunk.values]
                    f_cursor.executemany(insert_sql, data_tuples)
                    f_conn.commit()
                    
                    total_rows_migrated += len(df_chunk)
                    # Update status for large tables
                    if not dry_run:
                        print(f"{total_rows_migrated}...", end="", flush=True)

            o_conn.close()

            if total_rows_migrated == 0:
                print("ℹ️ (0 rows - Skipping)")
            elif not dry_run:
                print(f" ✅ DONE ({total_rows_migrated} rows total).")

        f_conn.close()
        
        if dry_run:
            print(f"\n🏆 DRY RUN COMPLETE: Batch processing logic verified.")
        else:
            print("\n🚀 DATA MIGRATION COMPLETE: All datasets synced successfully.")

    except Exception as e:
        print(f"\n❌ DATA PUMP FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle to Fabric Data Pump")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    move_data_to_fabric(dry_run=args.dry_run)