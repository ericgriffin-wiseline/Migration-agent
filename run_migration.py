import subprocess
import sys
import os
import msal

# --- CONFIGURATION ---
# Well-known Client ID for Azure PowerShell (pre-approved in most tenants)
CLIENT_ID = "1950a258-227b-4e31-a9cf-717495945fc2" 
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://database.windows.net//.default"]

SCRIPTS = [
    ("oracle_scraper.py", "Discovery: Scraping Oracle Metadata"),
    ("migration_orchestrator.py", "AI Logic: Generating Fabric T-SQL"),
    ("integrity_validator.py", "Audit: Capturing Source Snapshots"),
    ("fabric_executor.py", "Infrastructure: Deploying Cloud Schema"),
    ("data_pump.py", "Execution: Pumping Data to Fabric")
]

def get_fabric_token():
    print("\n🔐 [SSO] Initializing Azure Single Sign-On for Fabric...")
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    
    # Check for cached accounts first (optional, but good for UX)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    else:
        # Trigger the browser popup ONCE
        result = app.acquire_token_interactive(scopes=SCOPES)
    
    if "access_token" in result:
        print("✅ Authentication Successful. Token cached for session.")
        return result["access_token"]
    else:
        print(f"❌ Authentication Failed: {result.get('error_description')}")
        sys.exit(1)

def run_script(script_name, args=[], token=None):
    env = os.environ.copy()
    if token:
        env["FABRIC_ACCESS_TOKEN"] = token # Inject token into child's environment
    
    cmd = [sys.executable, script_name] + args
    try:
        subprocess.run(cmd, check=True, env=env)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("=" * 60)
    print("🚀 ORACLE-TO-FABRIC ENTERPRISE CONTROL PLANE")
    print("=" * 60)

    # 1. Login Gate
    access_token = get_fabric_token()

    # 2. Dry Run Phase
    confirm_dry = input("\n👉 Start the Mock Migration (Dry Run)? (yes/no): ").lower().strip()
    if confirm_dry == 'yes':
        for script, desc in SCRIPTS:
            if not run_script(script, ["--dry-run"], token=access_token):
                print(f"\n❌ MOCK FAILURE at: {desc}")
                return
        print("\n✅ MOCK MIGRATION SUCCESSFUL.")

    # 3. Real Migration Phase
    confirm_real = input("\n🔥 Ready to start the REAL migration? (yes/no): ").lower().strip()
    if confirm_real == 'yes':
        for script, desc in SCRIPTS:
            print(f"\n--- EXECUTING: {desc} ---")
            if not run_script(script, [], token=access_token):
                print(f"\n❌ MIGRATION FAILED at: {desc}")
                sys.exit(1)
            
            # Safety Interlock
            if input(f"\n❓ Step Complete. Proceed to next? (yes/no): ").lower() != 'yes':
                print("🛑 Emergency Stop.")
                sys.exit(1)
        print("\n🏆 MIGRATION COMPLETE.")

if __name__ == "__main__":
    main()