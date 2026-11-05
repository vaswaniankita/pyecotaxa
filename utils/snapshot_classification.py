"""Save every object's current EcoTaxa classification to a CSV (restore point).

Columns: object_id (EcoTaxa id), orig_id, classif_id, classif_qual
(V validated, D dubious, P predicted, empty unclassified).

Example:
  python snapshot_classification.py 17222 classification_snapshot.csv
"""
import argparse

import pandas as pd

from pyecotaxa.remote import Remote

PAGE_SIZE = 20000


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_id", type=int)
    parser.add_argument("out")
    args = parser.parse_args()

    remote = Remote()
    pages = []
    total = None
    while total is None or sum(len(page) for page in pages) < total:
        start = sum(len(page) for page in pages)
        response = remote.post(
            f"object_set/{args.project_id}/query",
            params={"fields": "obj.orig_id,obj.classif_id,obj.classif_qual", "order_field": "obj.objid",
                    "window_start": start, "window_size": PAGE_SIZE},
            json={},
        )
        total = response["total_ids"]
        if not response["object_ids"]:
            break
        page = pd.DataFrame(response["details"], columns=["orig_id", "classif_id", "classif_qual"])
        page.insert(0, "object_id", response["object_ids"])
        pages.append(page)
        print(f"{start + len(page)} / {total}", flush=True)

    snapshot = pd.concat(pages, ignore_index=True)
    assert len(snapshot) == total and snapshot["object_id"].is_unique, "incomplete snapshot"
    snapshot["classif_id"] = snapshot["classif_id"].astype("Int64")
    snapshot.to_csv(args.out, index=False)
    print(f"{args.out}: {len(snapshot)} objects")
    print(snapshot["classif_qual"].fillna("unclassified").value_counts().to_string())


if __name__ == "__main__":
    main()
