"""Push machine predictions to EcoTaxa as automatic classifications, unclassified objects only.

Predictions (object_prediction, object_maxp) come from an EcoTaxa TSV export of the
project and are mapped to taxon ids with a CSV (prediction,taxon_id,taxon_name).
Works sample by sample: right before each write it asks EcoTaxa which objects in
those samples are *currently* unclassified and sends only those, so objects
validated in the meantime are never touched. EcoTaxa's classify_auto itself also
leaves validated and dubious objects' classification unchanged.

Every object sent is appended to --log (objid, orig_id, taxon_id, score).

Example (test on 20 objects, then everything):
  python push_predictions.py 17222 export.zip prediction_taxa.csv --log pushed.csv --limit 20
  python push_predictions.py 17222 export.zip prediction_taxa.csv --log pushed.csv
"""
import argparse
import csv
import zipfile

import pandas as pd

from pyecotaxa.remote import Remote

SAMPLES_PER_BATCH = 20


def read_predictions(export_path):
    with zipfile.ZipFile(export_path) as archive:
        tsv_name = next(name for name in archive.namelist() if name.endswith(".tsv"))
        with archive.open(tsv_name) as tsv:
            table = pd.read_csv(tsv, sep="\t", dtype=str, keep_default_na=False,
                                usecols=["object_id", "object_prediction", "object_maxp"])
    return table.set_index("object_id")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_id", type=int)
    parser.add_argument("export", help="EcoTaxa TSV export (zip) with object_prediction and object_maxp")
    parser.add_argument("mapping", help="CSV with columns prediction,taxon_id")
    parser.add_argument("--log", required=True, help="CSV to append every pushed object to")
    parser.add_argument("--limit", type=int, help="stop after this many objects")
    parser.add_argument("--dry-run", action="store_true", help="report what would be sent, write nothing")
    args = parser.parse_args()

    predictions = read_predictions(args.export)
    taxon_ids = pd.read_csv(args.mapping).set_index("prediction")["taxon_id"]
    unmapped = set(predictions["object_prediction"]) - set(taxon_ids.index)
    if unmapped:
        raise SystemExit(f"Predictions without a taxon in {args.mapping}: {sorted(unmapped)}")
    predictions["taxon_id"] = predictions["object_prediction"].map(taxon_ids).astype(int)
    predictions["score"] = predictions["object_maxp"].astype(float)
    assert predictions["score"].between(0, 1).all()

    remote = Remote()
    samples = remote.get("samples/search", params={"project_ids": str(args.project_id), "id_pattern": ""})
    sample_ids = sorted(sample["sampleid"] for sample in samples)

    pushed = 0
    with open(args.log, "a", newline="") as log_file:
        log = csv.writer(log_file)
        for start in range(0, len(sample_ids), SAMPLES_PER_BATCH):
            batch_samples = ",".join(map(str, sample_ids[start:start + SAMPLES_PER_BATCH]))
            response = remote.post(
                f"object_set/{args.project_id}/query",
                params={"fields": "obj.orig_id,obj.classif_qual", "window_size": 1_000_000},
                json={"statusfilter": "U", "samples": batch_samples},
            )
            objects = pd.DataFrame(response["details"], columns=["orig_id", "classif_qual"])
            objects["objid"] = response["object_ids"]
            assert objects["classif_qual"].isna().all(), "query returned classified objects"
            objects = objects.join(predictions[["taxon_id", "score"]], on="orig_id", how="inner")
            if args.limit is not None:
                objects = objects.head(args.limit - pushed)
            if objects.empty:
                continue

            if not args.dry_run:
                updated = remote.post("object_set/classify_auto", json={
                    "target_ids": objects["objid"].tolist(),
                    "classifications": objects["taxon_id"].tolist(),
                    "scores": objects["score"].tolist(),
                    "keep_log": True,
                })
                if updated != len(objects):
                    print(f"warning: EcoTaxa updated {updated} of {len(objects)} objects in samples {batch_samples}")
                log.writerows(objects[["objid", "orig_id", "taxon_id", "score"]].itertuples(index=False))
                log_file.flush()
            pushed += len(objects)
            print(f"samples {start + 1}-{min(start + SAMPLES_PER_BATCH, len(sample_ids))} / {len(sample_ids)}: "
                  f"{len(objects)} objects, {pushed} total{' (dry run)' if args.dry_run else ''}", flush=True)
            if args.limit is not None and pushed >= args.limit:
                break
    print(f"done: {pushed} objects{' would be' if args.dry_run else ''} pushed")


if __name__ == "__main__":
    main()
