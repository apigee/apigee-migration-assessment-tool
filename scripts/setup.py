import os
import configparser
import argparse

def _status(message, status):
    if status == 0: # Completed
        print(f"  [\033[92m✓\033[0m] {message}")
    elif status == 1: # Skipped
        print(f"  [\033[93m○\033[0m] {message}")
    elif status == 2: # Warning
        print(f"  [\033[91m✗\033[0m] {message}")

def main():
    parser = argparse.ArgumentParser(description='Setup script for Apigee Migration Assessment Tool.')
    parser.add_argument('-o', '--org', help='Apigee source organization')
    args = parser.parse_args()

    print("--- Preparing local environment ---")

    # --- Handle input.properties ---
    source_org = args.org or ""
    
    if not os.path.exists("input.properties"):
        # Assuming shutil is available and imported in the original context, or needs to be added.
        # For this specific task, we focus on escaping. If shutil is missing, it's a separate issue.
        import shutil
        shutil.copy("sample/inputs/saas.input.properties", "input.properties")
        _status("Created 'input.properties' from saas sample.", 0)

    config = configparser.ConfigParser()
    config.read('input.properties')
    current_org = config.get('inputs', 'SOURCE_ORG', fallback="sample-saas-project-1")

    if not source_org:
        if current_org == "sample-saas-project-1" or not current_org:
            source_org = input("Enter your Apigee Source Org Name: ")
        else:
            source_org = current_org
    
    config.set('inputs', 'SOURCE_ORG', source_org)
    with open('input.properties', 'w') as configfile:
        config.write(configfile)
    _status(f"Set SOURCE_ORG in 'input.properties' to '{source_org}'.", 0)
    
    # Set proper permissions for input.properties (readable by Docker container)
    os.chmod('input.properties', 0o644)
    _status("Set proper permissions for 'input.properties' (readable by Docker).", 0)

    # --- Final directory and permission checks ---
    if not os.path.exists("output"):
        os.makedirs("output")
        _status("Created 'output' directory.", 0)
    else:
        _status("'output' directory already exists.", 1)

    # Set proper permissions for output directory (writable by Docker container)
    os.chmod("output", 0o777)
    _status("Set proper permissions for 'output' directory (writable by Docker).", 0)

    print("\nSetup is complete.")

if __name__ == "__main__":
    main()