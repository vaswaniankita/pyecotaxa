import pandas as pd
from pathlib import Path
from pyecotaxa import Archive
import concurrent.futures
from tqdm import tqdm

def validate_archive(archive_path):
    """Validate a single archive and return validation results."""
    try:
        with Archive(archive_path) as archive:
            # Validate the archive structure
            archive.validate()
            
            # Read the TSV file to get some basic stats
            for tsv_fn, tsv in archive.iter_tsv():
                n_rows = len(tsv)
                n_images = tsv['img_file_name'].nunique()
                return {
                    'status': 'valid',
                    'rows': n_rows,
                    'unique_images': n_images,
                    'error': None
                }
    except Exception as e:
        return {
            'status': 'invalid',
            'rows': 0,
            'unique_images': 0,
            'error': str(e)
        }

def main():
    # Directory containing the archives
    archive_dir = Path('/gpfs/work/vaswani/phytodive_daily_archives')
    
    # Get all zip files
    archive_files = list(archive_dir.glob('*.zip'))
    print(f"Found {len(archive_files)} archives to validate")
    
    # Validate archives in parallel
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Submit all validation tasks
        future_to_archive = {
            executor.submit(validate_archive, archive_path): archive_path
            for archive_path in archive_files
        }
        
        # Process results as they complete
        for future in tqdm(concurrent.futures.as_completed(future_to_archive), 
                         total=len(archive_files),
                         desc="Validating archives"):
            archive_path = future_to_archive[future]
            try:
                result = future.result()
                results.append({
                    'archive': archive_path.name,
                    **result
                })
            except Exception as e:
                results.append({
                    'archive': archive_path.name,
                    'status': 'error',
                    'rows': 0,
                    'unique_images': 0,
                    'error': str(e)
                })
    
    # Print summary
    print("\nValidation Summary:")
    print("-" * 80)
    print(f"{'Archive':<40} {'Status':<10} {'Rows':<10} {'Images':<10} {'Error':<20}")
    print("-" * 80)
    
    valid_count = 0
    invalid_count = 0
    total_rows = 0
    total_images = 0
    
    for result in sorted(results, key=lambda x: x['archive']):
        print(f"{result['archive']:<40} {result['status']:<10} "
              f"{result['rows']:<10} {result['unique_images']:<10} "
              f"{result['error'] or '':<20}")
        
        if result['status'] == 'valid':
            valid_count += 1
            total_rows += result['rows']
            total_images += result['unique_images']
        else:
            invalid_count += 1
    
    print("-" * 80)
    print(f"\nSummary:")
    print(f"Total archives: {len(results)}")
    print(f"Valid archives: {valid_count}")
    print(f"Invalid archives: {invalid_count}")
    print(f"Total rows: {total_rows}")
    print(f"Total unique images: {total_images}")

if __name__ == '__main__':
    main() 