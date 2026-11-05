"""Fill columns of a TSV table from a second table, joined on a key.

Each --fill names source columns for the --target columns (in order) and a label.
A row takes the first group whose columns are all present; rows with no complete
group are left as they are. List the target columns themselves first to keep
existing values. Source columns whose name clashes with a TSV column get "_src".

Example (positions from envAddedFPS.csv):
  python fill_position.py final_phytodive_datatable_timebins_fps_annotation_ecotaxa.tsv \\
      envAddedFPS.csv out.tsv --key img_file_name --source-key filename \\
      --strip '^https?://localhost:\\d+/' --target obj_lat,obj_lon --label obj_pos_source \\
      --fill obj_lat,obj_lon=track --fill lat_313,lon_313=313 --fill Lat,Lon=station
"""
import argparse

import pandas as pd

MISSING = ["", "NaN", "nan"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tsv")
    parser.add_argument("source", help="CSV, or TSV if it ends in .tsv")
    parser.add_argument("out")
    parser.add_argument("--key", required=True, help="key column in the TSV")
    parser.add_argument("--source-key", help="key column in the source (default: --key)")
    parser.add_argument("--strip", help="regex removed from the source key before matching")
    parser.add_argument("--target", required=True, help="comma-separated columns to fill")
    parser.add_argument("--fill", action="append", required=True, metavar="COLUMNS=LABEL")
    parser.add_argument("--label", help="column recording which --fill group was used")
    args = parser.parse_args()
    targets = args.target.split(",")

    table = pd.read_csv(args.tsv, sep="\t", dtype=str, keep_default_na=False)
    source_sep = "\t" if args.source.endswith(".tsv") else ","
    source = pd.read_csv(args.source, sep=source_sep, dtype=str, keep_default_na=False)
    source = source.apply(lambda column: column.str.strip())
    source["__key"] = source[args.source_key or args.key]
    if args.strip:
        source["__key"] = source["__key"].str.replace(args.strip, "", regex=True)

    merged = table.merge(source, left_on=args.key, right_on="__key", how="left", suffixes=("", "_src"),
                         validate="many_to_one", indicator=True)
    unmatched = (merged["_merge"] == "left_only").sum()
    print(f"{len(merged)} rows, {unmatched} without a match in {args.source}")

    def complete(columns):
        return ~merged[columns].fillna("").isin(MISSING).any(axis=1)

    for column in targets + ([args.label] if args.label else []):
        if column not in merged:
            merged[column] = ""
    unfilled = pd.Series(True, index=merged.index)
    for fill in args.fill:
        columns, label = fill.rsplit("=", 1)
        columns = columns.split(",")
        take = unfilled & complete(columns)
        merged.loc[take, targets] = merged.loc[take, columns].to_numpy()
        if args.label:
            merged.loc[take, args.label] = label
        unfilled &= ~take
        print(f"{label:>10}: {take.sum()} rows from {','.join(columns)}")
    print(f"{'none':>10}: {unfilled.sum()} rows")

    new_columns = [column for column in targets + [args.label] if column and column not in table.columns]
    out = merged[list(table.columns) + new_columns]
    out.columns = ["" if column.startswith("Unnamed: ") else column for column in out.columns]
    out.to_csv(args.out, sep="\t", index=False)


if __name__ == "__main__":
    main()
