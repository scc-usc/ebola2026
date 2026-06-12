# Ebola 2026 Observed Data in Hubverse

This repository converts source surveillance CSV files into a single [hubverse-style](hubverse.io) observed data file.

## Data Source

Source data are from:

https://github.com/INRB-UMIE/BDBV2026-Data/

## Files

- `source_links.txt`: list of source CSV URLs (one URL per line).
- `convert_to_hubverse.py`: conversion script that reads all links and consolidates output.
- `hubverse_observed_data.csv`: generated hubverse observed data file.

## Run Locally

```bash
python convert_to_hubverse.py --links-file source_links.txt --output hubverse_observed_data.csv
```

## GitHub Actions Automation

The workflow in `.github/workflows/generate-hubverse-data.yml` runs:

- on demand (`workflow_dispatch`)
- automatically every other day (03:00 UTC, via cron)

If the generated file changes, the workflow commits and pushes the updated `hubverse_observed_data.csv`.
