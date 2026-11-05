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
            
            # Print contents of the zip file
            print("\nZip file contents:")
            for file in zip_ref.namelist():
                print(f"- {file}")
            
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
    print(f"Found {len(archive_files)} archives")
    
    # List available archives
    print("\nAvailable archives:")
    for i, archive in enumerate(archive_files, 1):
        print(f"{i}. {archive.name}")
    
    # Get user selection
    while True:
        try:
            selection = int(input("\nEnter the number of the archive to push (or 0 to exit): "))
            if selection == 0:
                print("Exiting...")
                return
            if 1 <= selection <= len(archive_files):
                break
            print(f"Please enter a number between 1 and {len(archive_files)}")
        except ValueError:
            print("Please enter a valid number")
    
    archive_path = archive_files[selection - 1]
    print(f"\nSelected archive: {archive_path.name}")
    
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
    
    # Validate the zip file first
    is_valid, message = validate_zip_file(archive_path)
    if not is_valid:
        print(f"Error: {message}")
        return
        
    print(f"Validating {archive_path.name}...")
    try:
        # Push the archive using FTP transport for large files
        remote.push(
            [(str(archive_path), int(project_id))],
            n_parallel=1,
            force=True,  # Force re-upload
            mode=ImportMode.CREATE,
            transport=Transport.FTP,
            validate=True
        )
        print(f"Successfully pushed {archive_path.name}")
        
    except JobError as e:
        print(f"\nImport job failed for {archive_path.name}:")
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
                print("\nJob details:")
                print(f"State: {job['state']}")
                print(f"Progress: {job.get('progress', 'N/A')}")
                print(f"Progress message: {job.get('progress_msg', 'N/A')}")
                print(f"Error: {job.get('error', 'N/A')}")
                print(f"Job ID: {job.get('id', 'N/A')}")
                print(f"Job type: {job.get('type', 'N/A')}")
                print(f"Job parameters: {job.get('params', 'N/A')}")
                
                # Get full job details
                try:
                    full_job = remote._get_job(job['id'])
                    print("\nFull job details:")
                    print(f"Job state: {full_job.get('state', 'N/A')}")
                    print(f"Job progress: {full_job.get('progress', 'N/A')}")
                    print(f"Job progress message: {full_job.get('progress_msg', 'N/A')}")
                    print(f"Job error: {full_job.get('error', 'N/A')}")
                    print(f"Job parameters: {full_job.get('params', 'N/A')}")
                except Exception as job_error:
                    print(f"Could not get full job details: {str(job_error)}")
        except Exception as job_error:
            print(f"Could not get job details: {str(job_error)}")
            
    except Exception as e:
        print(f"Error pushing {archive_path.name}: {str(e)}")
        print("Full error details:")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 