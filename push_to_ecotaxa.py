import os
from pathlib import Path
from pyecotaxa import Remote, Transport, ImportMode
from pyecotaxa.remote import JobError
from tqdm import tqdm
import time
import zipfile

def validate_zip_file(file_path):
    """Validate that a file is a proper zip file."""
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Test the zip file integrity
            if zip_ref.testzip() is not None:
                return False, "Zip file contains corrupted files"
            
            # Check if it contains any files
            if not zip_ref.namelist():
                return False, "Zip file is empty"
            
            # Check if it contains a TSV file
            tsv_files = [f for f in zip_ref.namelist() if f.endswith('.tsv')]
            if not tsv_files:
                return False, "Zip file does not contain any TSV files"
            
            return True, "Valid zip file"
    except zipfile.BadZipFile:
        return False, "File is not a valid zip file"
    except Exception as e:
        return False, f"Error validating zip file: {str(e)}"

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
        print(f"\nProcessing {archive_path.name}...")
        
        # Validate the zip file first
        is_valid, message = validate_zip_file(archive_path)
        if not is_valid:
            print(f"Error: {message}")
            print(f"Skipping {archive_path.name}")
            continue
            
        print(f"Validating {archive_path.name}...")
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
            print(f"Successfully pushed {archive_path.name}")
            
        except JobError as e:
            print(f"Import job failed for {archive_path.name}:")
            print(f"Error message: {str(e)}")
            
            # Try to get more details about the job
            try:
                jobs = remote._get_jobs(
                    type="FileImport",
                    params={
                        "prj_id": int(project_id),
                        "req": {"source_path": str(archive_path), "update_mode": ImportMode.CREATE.value},
                    },
                )
                if jobs:
                    job = jobs[0]
                    print(f"Job details:")
                    print(f"State: {job['state']}")
                    print(f"Progress: {job.get('progress', 'N/A')}")
                    print(f"Progress message: {job.get('progress_msg', 'N/A')}")
                    print(f"Error: {job.get('error', 'N/A')}")
            except Exception as job_error:
                print(f"Could not get job details: {str(job_error)}")
                
        except Exception as e:
            print(f"Error pushing {archive_path.name}: {str(e)}")
            print("Full error details:")
            import traceback
            traceback.print_exc()
    
    print("\nAll archives processed!")
    print("Please check the EcoTaxa web interface to verify the uploads.")

if __name__ == '__main__':
    main() 