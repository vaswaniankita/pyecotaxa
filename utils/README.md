# Helper scripts

Scripts used to prepare, push, update and check EcoTaxa projects with pyecotaxa
(developed for the Phytodive / LP2022 CPICS project 17222). Run any of them with
`--help` for options and examples.

| Script | Purpose |
|---|---|
| `create_daily_archives.py` | Build one EcoTaxa import archive (TSV + images) per day from the full table (HPC paths) |
| `validate_archives.py` | Check the daily archives before import |
| `push_to_ecotaxa.py` | Interactively push one archive to a project (FTP, create mode) |
| `fill_position.py` | Fill columns (e.g. positions) of a TSV from a second table joined on a key |
| `make_update_archive.py` | Build metadata-only update archives (e.g. positions, depth) from a TSV |
| `snapshot_classification.py` | Save every object's current classification to a CSV (restore point) |
| `push_predictions.py` | Push machine predictions as automatic classifications to unclassified objects only |
| `prediction_taxa.csv` | Model class to EcoTaxa taxon mapping used for project 17222 |
| `compare_dwc.py` | Compare a Darwin Core export with an EcoTaxa TSV export of the same project |
| `mat2csv.py` | Convert the 2D variables of a MATLAB .mat file to CSV |

## Things learned the hard way

- Push archives with `Transport.FTP`. HTTP uploads are unpacked by the server into a
  folder, and the import job then cannot find the `.zip`.
- EcoTaxa skips TSV files whose name it has imported into the project before, and only
  reads TSVs whose name starts with `ecotaxa`. Give every update archive a new name
  (`make_update_archive.py --prefix`).
- `object_id` must be unique per object; this project uses the image file stem.
- Depth for the Darwin Core export must be in `object_depth_min` / `object_depth_max`;
  a free `object_depth` column is not used.
- Concentration formulae do not accept scientific notation (`0.827e-6` fails); write
  `0.827/1000000`.
