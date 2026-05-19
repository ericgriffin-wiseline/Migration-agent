import os
import json
import time
import argparse
from groq import Groq
from oracle_scraper import run_metadata_scraper
from migration_sequencer import generate_migration_sequence

# --- CONFIGURATION ---
GROQ_API_KEY = "your_api_key_here" 
client = Groq(api_key=GROQ_API_KEY)
MODEL_ID = "llama-3.3-70b-versatile" 

SCHEMA_FILE = "oracle_schema_map.json"
SEQUENCE_FILE = "migration_sequence.json"
RULES_FILE = "mapping_rules.json"
OUTPUT_DIR = "generated_sql"

def orchestrate_migration(dry_run=False):
    if dry_run:
        print("\n🏗️  [DRY RUN MODE] Starting Orchestration Simulation...")
    else:
        print("\n🏗️  Starting Enterprise Orchestrator (Groq Edition)...")

    # 1. Metadata & Sequence
    run_metadata_scraper(dry_run=dry_run)
    sequence = generate_migration_sequence(SCHEMA_FILE)

    # ALWAYS save the sequence file so downstream scripts can read it
    with open(SEQUENCE_FILE, "w") as f:
        json.dump(sequence, f, indent=4)

    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 2. Translation Loop
    mode_label = "[DRY RUN]" if dry_run else "[LIVE]"
    print(f"\n🚀 Initializing Groq Agent for {len(sequence)} tables {mode_label}...")
    
    if not dry_run:
        with open(SCHEMA_FILE, "r") as f:
            full_metadata = json.load(f)
        with open(RULES_FILE, "r") as f:
            mapping_rules = json.load(f)

    for table_name in sequence:
        if dry_run:
            print(f"   ∟ [MOCK] Creating simulated SQL artifact: {table_name}.sql")
            # Create a mock file so fabric_executor has something to "dry run" against
            file_path = os.path.join(OUTPUT_DIR, f"{table_name}.sql")
            with open(file_path, "w") as sql_file:
                sql_file.write(f"-- MOCK SQL FOR {table_name}\nCREATE TABLE {table_name} (MOCK_COL INT);")
            continue

        # --- LIVE MODE LOGIC ---
        print(f"   ∟ Translating: {table_name}...", end=" ", flush=True)
        table_metadata = full_metadata["tables"].get(table_name, [])
        prompt_content = f"""
        TASK: Convert Oracle Metadata to Microsoft Fabric Warehouse T-SQL.
        SOURCE TABLE: {table_name}
        METADATA: {json.dumps(table_metadata)}
        RULES: {json.dumps(mapping_rules)}
        
        CRITICAL REQUIREMENTS FOR FABRIC:
        1. DO NOT include 'PRIMARY KEY' or 'UNIQUE' constraints.
        2. Output ONLY the raw T-SQL 'CREATE TABLE' statement.
        3. Use standard data types as per mapping rules.
        """

        success = False
        retries = 0
        while not success and retries < 3:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_content}],
                    model=MODEL_ID,
                    temperature=0.1,
                )
                sql_code = chat_completion.choices[0].message.content.strip()
                sql_code = sql_code.replace("```sql", "").replace("```", "").strip()

                if sql_code:
                    file_path = os.path.join(OUTPUT_DIR, f"{table_name}.sql")
                    with open(file_path, "w") as sql_file:
                        sql_file.write(sql_code)
                    print("✅ DONE")
                    success = True
                    time.sleep(2) 
            except Exception as e:
                retries += 1
                time.sleep(5)

    if dry_run:
        print(f"\n🏆 DRY RUN FINISHED: All {len(sequence)} tables validated.")
        print(f"📝 [MOCK] Artifacts generated for testing.")
    else:
        print(f"\n🏆 MIGRATION SEQUENCE FINISHED.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    orchestrate_migration(dry_run=args.dry_run)