"""Compare an EcoTaxa Darwin Core export with an EcoTaxa TSV export of the same project.

Checks that every sample has an event and vice versa (eventID = sample_id), and per
event: date range against the objects' date/time, position against sample_lat /
sample_long, depth range against object_depth_min/max, and that the summed occurrence
counts do not exceed the number of validated (and, with --include-predicted,
predicted) objects. Non-living categories are not exported, so counts can be lower.

DWC is a DwC-A zip or a directory with event.txt, occurrence.txt and
extendedmeasurementorfact.txt. TSV_EXPORT is the zip of a general TSV export.

Example:
  python compare_dwc.py dwca.zip export__TSV_17222_20261105_0922.zip --include-predicted
"""
import argparse
import zipfile
from pathlib import Path

import pandas as pd

TSV_COLUMNS = ["object_id", "object_date", "object_time", "object_depth_min", "object_depth_max",
               "object_annotation_status", "sample_id", "sample_lat", "sample_long"]


def read_dwc(path, name):
    if Path(path).is_dir():
        return pd.read_csv(Path(path) / name, sep="\t", dtype=str, keep_default_na=False)
    with zipfile.ZipFile(path) as archive, archive.open(name) as member:
        return pd.read_csv(member, sep="\t", dtype=str, keep_default_na=False)


def read_tsv_export(path):
    with zipfile.ZipFile(path) as archive:
        tsv_name = next(name for name in archive.namelist() if name.endswith(".tsv"))
        with archive.open(tsv_name) as member:
            return pd.read_csv(member, sep="\t", dtype=str, keep_default_na=False, usecols=TSV_COLUMNS)


def report(label, mismatched, total, examples):
    print(f"{label}: {total - len(mismatched)} / {total} agree")
    if len(mismatched):
        print(examples.loc[mismatched].head(5).to_string())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dwc", help="DwC-A zip or directory")
    parser.add_argument("tsv_export", help="zip of an EcoTaxa general TSV export")
    parser.add_argument("--include-predicted", action="store_true", help="the DwC export included predicted objects")
    parser.add_argument("--tolerance", type=float, default=1e-4, help="for positions (degrees) and depths (m)")
    args = parser.parse_args()

    events = read_dwc(args.dwc, "event.txt").set_index("eventID")
    occurrences = read_dwc(args.dwc, "occurrence.txt")
    measurements = read_dwc(args.dwc, "extendedmeasurementorfact.txt")
    objects = read_tsv_export(args.tsv_export)

    objects["datetime"] = pd.to_datetime(objects["object_date"] + " " + objects["object_time"])
    for column in ["object_depth_min", "object_depth_max", "sample_lat", "sample_long"]:
        objects[column] = pd.to_numeric(objects[column], errors="coerce")
    exportable = ["validated"] + (["predicted"] if args.include_predicted else [])
    objects["exportable"] = objects["object_annotation_status"].isin(exportable)
    samples = objects.groupby("sample_id").agg(
        first=("datetime", "min"), last=("datetime", "max"),
        lat=("sample_lat", "first"), lon=("sample_long", "first"),
        depth_min=("object_depth_min", "min"), depth_max=("object_depth_max", "max"),
        objects=("object_id", "size"), exportable=("exportable", "sum"),
    )

    print(f"TSV export: {len(objects)} objects in {len(samples)} samples, "
          f"{objects['exportable'].sum()} {'/'.join(exportable)}")
    print(f"DwC export: {len(events)} events, {len(occurrences)} occurrences")
    print("occurrences by verification status:",
          occurrences["identificationVerificationStatus"].value_counts().to_dict())
    without_event = samples.index.difference(events.index)
    print(f"samples without event: {len(without_event)} {list(without_event[:10])}")
    print(f"events without sample: {len(events.index.difference(samples.index))}")
    if len(without_event):
        print("  exportable objects in those samples:", samples.loc[without_event, "exportable"].sum())

    compared = events.join(samples, how="inner")
    total = len(compared)

    dates = compared["eventDate"].str.split("/", expand=True).reindex(columns=[0, 1])
    dates[1] = dates[1].fillna(dates[0])
    compared["dwc_first"] = pd.to_datetime(dates[0]).dt.tz_localize(None)
    compared["dwc_last"] = pd.to_datetime(dates[1]).dt.tz_localize(None)
    wrong_dates = compared.index[(compared["dwc_first"] != compared["first"]) | (compared["dwc_last"] != compared["last"])]
    report("dates", wrong_dates, total, compared[["eventDate", "first", "last"]])

    for column in ["decimalLatitude", "decimalLongitude", "minimumDepthInMeters", "maximumDepthInMeters"]:
        compared[column] = pd.to_numeric(compared[column], errors="coerce")
    wrong_positions = compared.index[((compared["decimalLatitude"] - compared["lat"]).abs() > args.tolerance) |
                                     ((compared["decimalLongitude"] - compared["lon"]).abs() > args.tolerance)]
    report("positions", wrong_positions, total, compared[["decimalLatitude", "lat", "decimalLongitude", "lon"]])

    def depth_differs(dwc_column, sample_column):
        dwc, sample = compared[dwc_column], compared[sample_column]
        return (dwc.isna() != sample.isna()) | ((dwc - sample).abs() > args.tolerance)

    wrong_depths = compared.index[depth_differs("minimumDepthInMeters", "depth_min") |
                                  depth_differs("maximumDepthInMeters", "depth_max")]
    report("depths", wrong_depths, total,
           compared[["minimumDepthInMeters", "depth_min", "maximumDepthInMeters", "depth_max"]])
    print(f"  events without depth: {compared['minimumDepthInMeters'].isna().sum()}")

    counts = measurements[measurements["measurementType"].str.startswith("Count")]
    counts = counts.merge(occurrences[["occurrenceID", "eventID"]], on="occurrenceID")
    counted = pd.to_numeric(counts["measurementValue"]).groupby(counts["eventID"]).sum()
    compared["counted"] = counted.reindex(compared.index).fillna(0)
    too_many = compared.index[compared["counted"] > compared["exportable"]]
    report("counts <= exportable objects", too_many, total, compared[["counted", "exportable", "objects"]])
    print(f"  counted {int(compared['counted'].sum())} of {int(compared['exportable'].sum())} exportable objects "
          f"(the rest are non-living or unmapped categories)")


if __name__ == "__main__":
    main()
