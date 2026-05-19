import json
from collections import deque, defaultdict

def generate_migration_sequence(input_file):
    print(f"📂 Loading schema map from {input_file}...")
    
    with open(input_file, "r") as f:
        data = json.load(f)
    
    tables = list(data["tables"].keys())
    dependencies = data["dependencies"]
    
    adj = defaultdict(list)
    in_degree = {table: 0 for table in tables}
    
    for dep in dependencies:
        parent = dep["parent_table"]
        child = dep["child_table"]
        
        # Only track dependencies between tables we are actually migrating
        if parent in tables and child in tables:
            # FIX: Ignore self-references (e.g., EMPLOYEES referencing EMPLOYEES)
            if parent == child:
                print(f"   ℹ️  Self-reference detected in {child} (Skipping for sequence logic)")
                continue
                
            adj[parent].append(child)
            in_degree[child] += 1

    queue = deque([table for table in tables if in_degree[table] == 0])
    sequence = []

    while queue:
        current = queue.popleft()
        sequence.append(current)
        
        for neighbor in adj[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sequence) != len(tables):
        print("⚠️ WARNING: Circular dependency detected.")
        remaining = set(tables) - set(sequence)
        print(f"Tables missed: {remaining}")
    else:
        print("✅ Success: Optimal migration sequence established.")

    return sequence

if __name__ == "__main__":
    try:
        migration_order = generate_migration_sequence("oracle_schema_map.json")
        
        print("\n🚀 PROPOSED MIGRATION SEQUENCE:")
        for i, table in enumerate(migration_order, 1):
            print(f"   {i}. {table}")
            
        with open("migration_sequence.json", "w") as f:
            json.dump(migration_order, f, indent=4)
            
    except FileNotFoundError:
        print("❌ ERROR: 'oracle_schema_map.json' not found.")