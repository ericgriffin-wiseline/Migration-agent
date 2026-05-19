import oracledb
import json
import os
import argparse

# Configuration settings
config = {
    "user": "ERIC_DEV",
    "password": "Eric_Project_123",
    "dsn": "127.0.0.1:1521/xepdb1" 
}

def run_metadata_scraper(dry_run=False):
    if dry_run:
        print("\n🕵️  [DRY RUN MODE] Simulating Metadata Scraping...")
    else:
        print("\n🚀 Initializing Enterprise Oracle Metadata Scraper...")
        
    conn = None
    try:
        # 1. Establish the connection (Crucial to test even in dry run)
        conn = oracledb.connect(
            user=config["user"].upper(), 
            password=config["password"], 
            dsn=config["dsn"]
        )
        cursor = conn.cursor()
        print("🔗 Connection Successful!")

        # --- STEP A: SCRAPE COLUMNS AND PRIMARY KEYS ---
        print("🔎 Interrogating Column Metadata...")
        column_query = """
        SELECT col.table_name, col.column_name, col.data_type, 
               (SELECT 'YES' FROM user_constraints cons 
                JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name
                WHERE cons.constraint_type = 'P' 
                AND cons.table_name = col.table_name 
                AND cols.column_name = col.column_name) as is_pk
        FROM user_tab_columns col
        ORDER BY col.table_name, col.column_id
        """
        cursor.execute(column_query)
        column_rows = cursor.fetchall()

        # --- STEP B: SCRAPE FOREIGN KEY RELATIONSHIPS (DEPENDENCIES) ---
        print("🔗 Mapping Table Relationships (Foreign Keys)...")
        fk_query = """
        SELECT 
            a.table_name AS child_table, 
            c_pk.table_name AS parent_table,
            b.column_name AS child_column
        FROM 
            user_constraints a
        JOIN 
            user_cons_columns b ON a.constraint_name = b.constraint_name
        JOIN 
            user_constraints c_pk ON a.r_constraint_name = c_pk.constraint_name
        WHERE 
            a.constraint_type = 'R'
        """
        cursor.execute(fk_query)
        fk_rows = cursor.fetchall()

        # 3. Build the Consolidated JSON structure
        final_output = {
            "tables": {},
            "dependencies": []
        }

        for table, column, dtype, is_pk in column_rows:
            if table not in final_output["tables"]:
                final_output["tables"][table] = []
            final_output["tables"][table].append({
                "column_name": column,
                "data_type": dtype,
                "is_primary_key": True if is_pk == 'YES' else False
            })

        for child, parent, col in fk_rows:
            final_output["dependencies"].append({
                "child_table": child,
                "parent_table": parent,
                "via_column": col
            })

        # --- STEP C: UNCONDITIONAL SAVE (Required for Pipeline Flow) ---
        output_file = "oracle_schema_map.json"
        
        # We always write the file so downstream scripts (Orchestrator) have data to read
        with open(output_file, "w") as f:
            json.dump(final_output, f, indent=4)
        
        if dry_run:
            print("-" * 30)
            print("✅ [DRY RUN SUCCESS]: Metadata successfully retrieved and parsed.")
            print(f"📝 [MOCK] Schema Map generated to support downstream simulations.")
            print(f"📊 Summary: {len(final_output['tables'])} Tables found, {len(final_output['dependencies'])} Relationships mapped.")
            print("-" * 30)
        else:
            print("-" * 30)
            print(f"✅ SUCCESS: Enterprise Blueprint Created.")
            print(f"📂 Location: {os.path.abspath(output_file)}")
            print(f"📊 Metadata: {len(final_output['tables'])} Tables | {len(final_output['dependencies'])} Relationships")
            print("-" * 30)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)
    finally:
        if conn:
            conn.close()
            print("🔌 Connection closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle Metadata Scraper")
    parser.add_argument("--dry-run", action="store_true", help="Run the script without saving the JSON output.")
    args = parser.parse_args()

    run_metadata_scraper(dry_run=args.dry_run)