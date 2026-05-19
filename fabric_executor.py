import pyodbc
import json
import os
import argparse
import struct

# --- CONFIGURATION ---
SERVER_ADDRESS = "6rlqav7popeedpf3bdns7qk4fm-bypqfuwvnu4efnp5hxcw2ptic4.datawarehouse.fabric.microsoft.com"
DATABASE_NAME = "Fabric_Destination"
USERNAME = "ericgriffin.wiseline@rackspace.com"

def deploy_schema_to_fabric(dry_run=False):
    token = os.environ.get("FABRIC_ACCESS_TOKEN")
    
    # 1. Build the Connection
    if token:
        # TOKEN-BASED AUTH (No popups)
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER_ADDRESS};DATABASE={DATABASE_NAME};Encrypt=yes;TrustServerCertificate=no;"
        token_bytes = token.encode("utf-16-le")
        token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
        attrs = {1256: token_struct} # 1256 = SQL_COPT_SS_ACCESS_TOKEN
    else:
        # FALLBACK (Manual popup if run standalone)
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER_ADDRESS};DATABASE={DATABASE_NAME};UID={USERNAME};Authentication=ActiveDirectoryInteractive;Encrypt=yes;TrustServerCertificate=no;"
        attrs = {}

    try:
        conn = pyodbc.connect(conn_str, attrs_before=attrs)
        cursor = conn.cursor()
        print(f"🔗 Connected to Fabric Warehouse (Auth: {'Token' if token else 'Interactive'}).")

        # ... (rest of your table creation logic from previous version) ...
        # [Note: Reuse the sequence loading and loop from your previous fabric_executor.py]
        
        # Load sequence
        with open("migration_sequence.json", "r") as f:
            sequence = json.load(f)

        for table in sequence:
            sql_file = f"generated_sql/{table}.sql"
            if os.path.exists(sql_file):
                if dry_run:
                    print(f"   ∟ [MOCK] Validated DDL for: {table}")
                else:
                    with open(sql_file, "r") as f:
                        cursor.execute(f.read())
                    conn.commit()
                    print(f"   ∟ Created table: {table} ✅")
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    deploy_schema_to_fabric(dry_run=args.dry_run)