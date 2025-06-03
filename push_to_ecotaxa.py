import os
from pathlib import Path
from pyecotaxa import Remote, Transport
from tqdm import tqdm

def main():
    # Directory containing the archives
    archive_dir = Path('/gpfs/work/vaswani/phytodive_daily_archives')
    
    # Get all zip files
    archive_files = sorted(list(archive_dir.glob('*.zip')))
    print(f"Found {len(archive_files)} archives to push")
    
    # Initialize Remote connection
    print("\nInitializing connection to EcoTaxa...")
    remote = Remote()
    
    # Login to EcoTaxa
    print("Please enter your EcoTaxa credentials:")
    username = input("Username: ")
    password = input("Password: ")
    
    print("\nLogging in...")
    remote.login(username, password)
    
    # Get project ID
    project_id = input("\nEnter the project ID to push to: ")
    
    # Push each archive
    print("\nPushing archives to EcoTaxa...")
    for archive_path in tqdm(archive_files, desc="Uploading archives"):
        print(f"\nPushing {archive_path.name}...")
        try:
            # Push the archive
            remote.push_archive(
                archive_path,
                project_id,
                transport=Transport.HTTP,  # Using HTTP transport
                import_mode="append"  # Append to existing data
            )
            print(f"Successfully pushed {archive_path.name}")
        except Exception as e:
            print(f"Error pushing {archive_path.name}: {str(e)}")
    
    print("\nAll archives processed!")
    print("Please check the EcoTaxa web interface to verify the uploads.")

if __name__ == '__main__':
    main() 