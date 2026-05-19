import oracledb
import json
import os
import argparse

# Using the same config from your scraper
config = {
    "user": "ERIC_DEV",
    "password": "Eric_Project_123",
    "dsn": "127.0.0.1:1521/xepdb1" 
}

def generate_integrity_report(dry_run=False):
    if dry_run:
        print("\n🕵️  [DRY RUN MODE] Simulating Enterprise Integrity Audit...")
    else:
        print("\n🕵️  Initializing Enterprise Integrity Audit...")
    
    # 1. Load the sequence we just migrated
    try:
        with open("migration_sequence.json", "r") as f:
            tables = json.load(f)
    except FileNotFoundError:
        print("❌ Error: migration_sequence.json not found. Run the orchestrator first.")
        return

    report = []
    conn = None

    try:
        conn = oracledb.connect(
            user=config["user"].upper(), 
            password=config["password"], 
            dsn=config["dsn"]
        )
        cursor = conn.cursor()
        print(f"🔗 Connected to Oracle. Validating access to {len(tables)} tables...\n")

        print(f"{'TABLE NAME':<20} | {'ROW COUNT':<10} | {'STATUS'}")
        print("-" * 45)

        for table in tables:
            # Get Row Count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            # Get Column Count
            cursor.execute(f"SELECT COUNT(*) FROM user_tab_columns WHERE table_name = '{table}'")
            cols = cursor.fetchone()[0]

            status_label = "✅ Validated" if dry_run else "✅ Captured"
            print(f"{table:<20} | {count:<10} | {status_label} ({cols} cols)")
            
            report.append({
                "table": table,
                "oracle_rows": count,
                "oracle_cols": cols,
                "migration_status": "Verified Source"
            })

        # 2. Conditional Save
        output_file = "migration_audit_report.json"
        if dry_run:
            print(f"\n✅ [DRY RUN SUCCESS]: Connectivity and table accessibility verified.")
            print(f"🚫 [ACTION]: No audit report written to {output_file}.")
        else:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=4)
            print(f"\n📊 AUDIT COMPLETE: '{output_file}' generated.")
            print("💡 Use this file to compare against Microsoft Fabric row counts.")

    except Exception as e:
        print(f"❌ Audit Error: {e}")
        exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle Integrity Validator")
    parser.add_argument("--dry-run", action="store_true", help="Validate table access without saving the report.")
    args = parser.parse_args()

    generate_integrity_report(dry_run=args.dry_run)