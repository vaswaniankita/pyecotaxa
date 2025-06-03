import os
from pathlib import Path
from pyecotaxa import Remote, Transport, ImportMode
from tqdm import tqdm
import time

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
    
    # Set FTP credentials
    remote.config["ftp_user"] = "ftp_plankton"
    remote.config["ftp_passwd"] = "Pl@nkt0n4Ecotaxa"
    
    # Get project ID
    project_id = input("\nEnter the project ID to push to: ")
    
    # Push each archive
    print("\nPushing archives to EcoTaxa...")
    for archive_path in tqdm(archive_files, desc="Uploading archives"):
        print(f"\nPushing {archive_path.name}...")
        try:
            # Push the archive using FTP transport for large files
            remote.push(
                [(str(archive_path), int(project_id))],
                n_parallel=1,
                force=False,
                mode=ImportMode.CREATE,
                transport=Transport.FTP,  # Using FTP instead of HTTP
                validate=True
            )
            
            # Wait for import to complete
            print(f"Waiting for import to complete for {archive_path.name}...")
            time.sleep(30)  # Give some time for the import to start
            
            # Check job status
            jobs = remote._get_jobs(
                type="FileImport",
                params={
                    "prj_id": int(project_id),
                    "req": {"source_path": str(archive_path), "update_mode": ImportMode.CREATE.value},
                },
            )
            
            if jobs:
                job = jobs[0]
                print(f"Job status: {job['state']}")
                if job['state'] == 'E':  # Error state
                    print(f"Job error: {job.get('error', 'No error message available')}")
                elif job['state'] == 'D':  # Done state
                    print(f"Successfully imported {archive_path.name}")
                else:
                    print(f"Job is still running with state: {job['state']}")
            
        except Exception as e:
            print(f"Error pushing {archive_path.name}: {str(e)}")
            print("Full error details:")
            import traceback
            traceback.print_exc()
    
    print("\nAll archives processed!")
    print("Please check the EcoTaxa web interface to verify the uploads.")

if __name__ == '__main__':
    main() 