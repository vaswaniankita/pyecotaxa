import pandas as pd
import os
import shutil
from datetime import datetime
from pathlib import Path
import pyecotaxa
from tqdm import tqdm
from multiprocessing import Pool
from functools import partial

def process_date(date, group, output_dir, image_dir):
    """Process a single date's data and create its archive."""
    print(f"\nProcessing date: {date}")
    
    # Create a temporary directory for this date
    temp_dir = Path(output_dir) / f"temp_{date.strftime('%Y%m%d')}"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Write the TSV file with ecotaxa_ prefix
        tsv_name = f"ecotaxa_export_{date.strftime('%Y%m%d')}.tsv"
        tsv_path = temp_dir / tsv_name
        group.to_csv(tsv_path, sep='\t', index=False)
        
        # Get unique image files for this date
        image_files = group['img_file_name'].unique()
        print(f"Found {len(image_files)} unique images")
        
        # Copy images to temp directory
        missing_files = []
        for img_file in tqdm(image_files, desc="Copying images"):
            src_path = Path(image_dir) / img_file
            if not src_path.exists():
                missing_files.append(img_file)
                continue
                
            # Create the directory structure in temp_dir
            dest_path = temp_dir / img_file
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the image
            shutil.copy2(src_path, dest_path)
        
        if missing_files:
            print(f"\nWarning: {len(missing_files)} images were missing:")
            for f in missing_files[:5]:  # Show first 5 missing files
                print(f"- {f}")
            if len(missing_files) > 5:
                print(f"... and {len(missing_files) - 5} more")
        
        # Create the archive with ecotaxa_ prefix
        archive_name = f"ecotaxa_export_{date.strftime('%Y%m%d')}.zip"
        archive_path = Path(output_dir) / archive_name
        
        print(f"Creating archive: {archive_name}")
        with pyecotaxa.Archive(archive_path, mode='w') as archive:
            # Add the TSV file with its new name
            with open(tsv_path, 'rb') as f:
                archive.write_member(tsv_name, f)
            
            # Add all images
            for img_file in tqdm(image_files, desc="Adding images to archive"):
                if img_file not in missing_files:
                    img_path = temp_dir / img_file
                    with open(img_path, 'rb') as f:
                        archive.write_member(img_file, f)
        
        print(f"Created archive: {archive_name}")
        print(f"Archive contains {len(group)} rows and {len(image_files) - len(missing_files)} images")
        
        return {
            'date': date,
            'archive_name': archive_name,
            'rows': len(group),
            'images': len(image_files) - len(missing_files),
            'missing_images': len(missing_files)
        }
        
    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")

def main():
    # Read the TSV file
    print("Reading TSV file...")
    df = pd.read_csv('final_phytodive_datatable_timebins_fps_annotation_ecotaxa.tsv', sep='\t', low_memory=False)
    
    # Print available columns
    print("\nAvailable columns:")
    for col in df.columns:
        print(f"- {col}")
    
    # Find date column
    date_columns = [col for col in df.columns if 'date' in col.lower()]
    if not date_columns:
        raise ValueError("No date column found in the TSV file")
    
    print("\nFound these potential date columns:")
    for col in date_columns:
        print(f"- {col}")
    
    # Use the first date column found
    date_column = date_columns[0]
    print(f"\nUsing column '{date_column}' for grouping")
    
    # Convert date column to datetime
    df[date_column] = pd.to_datetime(df[date_column])
    
    # Create output directory
    output_dir = Path('/gpfs/work/vaswani/phytodive_daily_archives')
    output_dir.mkdir(exist_ok=True)
    
    # Path to images
    image_dir = Path('/gpfs/work/vaswani/phytodive_images')
    
    # Group by date and convert to list of tuples
    date_groups = [(date, group) for date, group in df.groupby(date_column)]
    print(f"\nFound {len(date_groups)} dates to process")
    
    # Create a partial function with fixed arguments
    process_func = partial(process_date, 
                         output_dir=output_dir, 
                         image_dir=image_dir)
    
    # Use 16 processes
    n_processes = 16
    print(f"\nUsing {n_processes} processes")
    
    # Process dates in parallel
    with Pool(n_processes) as pool:
        results = list(tqdm(
            pool.starmap(process_func, date_groups),
            total=len(date_groups),
            desc="Processing dates"
        ))
    
    # Print summary
    print("\nProcessing Summary:")
    print("-" * 50)
    for result in sorted(results, key=lambda x: x['date']):
        print(f"Date: {result['date'].strftime('%Y-%m-%d')}")
        print(f"Archive: {result['archive_name']}")
        print(f"Rows processed: {result['rows']}")
        print(f"Images processed: {result['images']}")
        print(f"Missing images: {result['missing_images']}")
        print("-" * 50)
    
    print("\nDone!")

if __name__ == '__main__':
    main() 