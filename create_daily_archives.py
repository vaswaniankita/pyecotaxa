
import pandas as pd
import os
import shutil
from datetime import datetime
from pathlib import Path
from pyecotaxa import Archive, write_tsv
import tempfile
from multiprocessing import Pool
from functools import partial

def process_date(date_data, output_dir, image_dir):
    date, group_df = date_data

    # Create archive name based on date
    date_str = date.strftime('%Y%m%d')
    archive_path = output_dir / f'ecotaxa_{date_str}.zip'

    print(f"Processing {date_str}...")
    print(f"Number of rows: {len(group_df)}")
    print(f"Number of unique images: {group_df['img_file_name'].nunique()}")

    # Create a temporary directory for this day's files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)More actions

        # Write TSV file for this day
        tsv_file = temp_dir / f'ecotaxa_{date_str}.tsv'
        write_tsv(group_df, tsv_file)

        # Copy images for this day
        missing_images = []
        for img_file in group_df['img_file_name'].unique():
            src_path = image_dir / img_file
            if src_path.exists():
                dst_path = temp_dir / img_file
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            else:
                missing_images.append(img_file)

        if missing_images:
            print(f"Warning: {len(missing_images)} images not found for {date_str}")
            print("First 5 missing images:", missing_images[:5])

        # Create zip archive
        with Archive(archive_path, 'w') as archive:
            # Add TSV file
            with open(tsv_file, 'rb') as f:
                archive.write_member('export.tsv', f)

            # Add images
            for img_file in group_df['img_file_name'].unique():
                img_path = temp_dir / img_file
                if img_path.exists():
                    with open(img_path, 'rb') as f:
                        archive.write_member(img_file, f)

    print(f"Created archive: {archive_path}")
    print(f"Archive size: {archive_path.stat().st_size / (1024*1024):.2f} MB")
    print("-" * 50)

    return date_str, len(group_df), group_df['img_file_name'].nunique(), len(missing_images)

def main():
    # Read the TSV file
    tsv_path = 'final_phytodive_datatable_timebins_fps_annotation_ecotaxa.tsv'
        # check the column names
    print("Reading TSV file...")
    df = pd.read_csv(tsv_path, sep='\t', nrows=1)  # Read just the header
    print("\nAvailable columns:")
    for col in df.columns:
        print(f"- {col}")
    
    # Now read the full file with low_memory=False to avoid the warning
    print("\nReading full TSV file...")
    df = pd.read_csv(tsv_path, sep='\t', low_memory=False)

    if 'Unnamed: 0' in df.columns:Add commentMore actions
    print("\nDropping unnamed index column...")
    df = df.drop(columns=['Unnamed: 0'])
    
    # Find and rename all columns starting with 'obj_'
    obj_columns = [col for col in df.columns if col.startswith('obj_')]
    if obj_columns:
        print("\nRenaming columns from 'obj_' to 'object_' prefix:")
        rename_dict = {col: col.replace('obj_', 'object_', 1) for col in obj_columns}
        for old_col, new_col in rename_dict.items():
            print(f"- {old_col} -> {new_col}")
        df = df.rename(columns=rename_dict)
    
    # Create sample_id based on unique sample_time-bin values
    print("\nCreating sample_id column...")
    # Create a mapping of unique sample_time-bin values to integers
    unique_samples = df['sample_time-bin'].unique()
    sample_id_map = {sample: i+1 for i, sample in enumerate(unique_samples)}
    # Add the sample_id column
    df['sample_id'] = df['sample_time-bin'].map(sample_id_map)
    print(f"Created {len(sample_id_map)} unique sample IDs")
    
    # Use the specific date column
    date_column = 'object_Date'
    if date_column not in df.columns:
        raise ValueError(f"Column '{date_column}' not found in the TSV file")
    
    print(f"\nUsing column '{date_column}' for grouping")
    
    # Convert date column to datetime
    df[date_column] = pd.to_datetime(df[date_column])

    # Create output directory for archives
    output_dir = Path('/gpfs/work/vaswani/phytodive_daily_archives')
    output_dir.mkdir(exist_ok=True)

    # HPC image directory
    image_dir = Path('/gpfs/work/vaswani/LPcruises/rois')

    # Group by date
    date_groups = list(df.groupby(date_column))

    # Create a partial function with fixed arguments
    process_func = partial(process_date, 
                         output_dir=output_dir, 
                         image_dir=image_dir)
        # Use 16 processesAdd commentMore actions
    n_processes = 16
    print(f"\nUsing {n_processes} processes")

    # Process dates in parallel
    with Pool(n_processes) as pool:
        results = pool.map(process_func, date_groups)

    # Print summary
    print("\nProcessing Summary:")
    print("-" * 50)
    for date_str, n_rows, n_images, n_missing in results:
        print(f"Date: {date_str}")
        print(f"Rows processed: {n_rows}")
        print(f"Images processed: {n_images}")
        print(f"Missing images: {n_missing}")
        print("-" * 50)

	if __name__ == '__main__':
