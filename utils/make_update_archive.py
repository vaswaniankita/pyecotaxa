"""Build EcoTaxa metadata-update archives (TSV only, no images) from a filled TSV.

Keeps rows whose --label-column is one of --labels (all rows without --labels;
optionally one --date) and that have a value in every column, drops duplicate
image files, derives object_id from the image file name and renames obj_* columns
to object_*. --copy SOURCE=TARGET adds TARGET as a copy of SOURCE first. With
--per-day, OUT is a directory that gets one update_YYYYMMDD.zip per obj_Date.

Example (test day, filled positions only):
  python make_update_archive.py filled.tsv update_20220622.zip --date 2022-06-22 \\
      --labels 313,station --columns obj_lat,obj_lon,obj_pos_source

Example (depth into EcoTaxa's depth fields, all days):
  python make_update_archive.py filled.tsv update_depth --per-day --prefix depth \\
      --copy obj_depth=obj_depth_min --copy obj_depth=obj_depth_max \\
      --columns obj_depth_min,obj_depth_max
"""
import argparse
from pathlib import Path

import pandas as pd

from pyecotaxa import Archive


def write_archive(rows, columns, label_column, path):
    update = pd.DataFrame({"object_id": rows["img_file_name"].map(lambda name: Path(name).stem)})
    for column in columns:
        values = pd.to_numeric(rows[column], errors="coerce")
        is_text = column == label_column or values.isna().any()
        update[column] = rows[column] if is_text else values
    update = update.rename(columns=lambda column: column.replace("obj_", "object_", 1))
    assert update["object_id"].is_unique

    with Archive(path, "w") as archive:
        archive.write_tsv(update, f"ecotaxa_{path.stem}.tsv")
    counts = ", ".join(f"{label}: {count}" for label, count in rows[label_column].value_counts().items())
    print(f"{path.name}: {len(update)} objects ({counts})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tsv")
    parser.add_argument("out", type=Path, help="zip archive to write (directory with --per-day)")
    parser.add_argument("--columns", required=True, help="comma-separated columns to include")
    parser.add_argument("--labels", help="comma-separated labels of rows to include (default: all)")
    parser.add_argument("--label-column", default="obj_pos_source")
    parser.add_argument("--date", help="only rows with this obj_Date (YYYY-MM-DD)")
    parser.add_argument("--per-day", action="store_true", help="write one archive per obj_Date")
    parser.add_argument("--copy", action="append", default=[], metavar="SOURCE=TARGET")
    parser.add_argument("--prefix", default="update",
                        help="per-day archive name prefix; EcoTaxa skips TSV names it has imported before")
    args = parser.parse_args()
    columns = args.columns.split(",")

    table = pd.read_csv(args.tsv, sep="\t", dtype=str, keep_default_na=False)
    for copy in args.copy:
        source, target = copy.split("=")
        table[target] = table[source]
    selected = (table[columns] != "").all(axis=1)
    if args.labels:
        selected &= table[args.label_column].isin(args.labels.split(","))
    if args.date:
        selected &= table["obj_Date"] == args.date
    rows = table[selected].drop_duplicates("img_file_name")

    if not args.per_day:
        write_archive(rows, columns, args.label_column, args.out)
        return
    args.out.mkdir(exist_ok=True)
    for date, day_rows in rows.groupby("obj_Date"):
        write_archive(day_rows, columns, args.label_column, args.out / f"{args.prefix}_{date.replace('-', '')}.zip")


if __name__ == "__main__":
    main()
