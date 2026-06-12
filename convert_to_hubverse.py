from __future__ import annotations

import argparse
import csv
import io
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

MANDATORY_OUTPUT_COLUMNS = ["target_end_date", "target", "location", "observation"]


def github_blob_to_raw(url: str) -> str:
    """Convert GitHub blob URLs to raw content URLs."""
    if "github.com" not in url or "/blob/" not in url:
        return url
    return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")


def filename_from_url(url: str) -> str:
    path = urlparse(url).path
    return Path(path).name


def normalize_header(name: str) -> str:
    return str(name).strip().lower()


def pick_column(candidates: list[str], options: list[str]) -> str | None:
    option_set = {normalize_header(opt): opt for opt in options}
    for candidate in candidates:
        if candidate in option_set:
            return option_set[candidate]
    return None


def parse_date_to_iso(value: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    known_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]
    for fmt in known_formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fall back to ISO-like parsing for datetime strings.
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_observation(value: str) -> int | float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def read_csv_from_url(raw_url: str) -> tuple[list[str], list[dict[str, str]]]:
    with urlopen(raw_url) as response:
        content = response.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise ValueError(f"No headers found in {raw_url}")
    rows = list(reader)
    return list(reader.fieldnames), rows


def convert_single_csv(url: str) -> list[dict[str, object]]:
    raw_url = github_blob_to_raw(url)
    source_filename = filename_from_url(url)
    target = source_filename.replace(".csv", "")

    fieldnames, rows = read_csv_from_url(raw_url)
    normalized_to_original = {normalize_header(name): name for name in fieldnames}

    location_col = pick_column(["nom", "location"], list(normalized_to_original.keys()))
    date_col = pick_column(["date", "target_end_date"], list(normalized_to_original.keys()))

    if location_col is None or date_col is None:
        raise ValueError(
            f"Missing required columns in {source_filename}. "
            f"Found columns: {fieldnames}"
        )

    location_col_name = normalized_to_original[location_col]
    date_col_name = normalized_to_original[date_col]

    value_columns = [
        name for name in fieldnames if name not in {location_col_name, date_col_name}
    ]
    if not value_columns:
        raise ValueError(
            f"Could not find value column in {source_filename}. "
            f"Found columns: {fieldnames}"
        )

    value_col_name = value_columns[0]

    out: list[dict[str, object]] = []
    for row in rows:
        target_end_date = parse_date_to_iso(row.get(date_col_name, ""))
        location = row.get(location_col_name, "")
        observation = parse_observation(row.get(value_col_name, ""))

        if target_end_date is None or observation is None:
            continue

        location_text = str(location).strip()
        if not location_text:
            continue

        out.append(
            {
                "target_end_date": target_end_date,
                "target": target,
                "location": location_text,
                "observation": observation,
            }
        )

    return out


def read_links(links_file: Path) -> list[str]:
    lines = links_file.read_text(encoding="utf-8").splitlines()
    links = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    if not links:
        raise ValueError(f"No URLs found in {links_file}")
    return links


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert multiple INSP source CSVs into one hubverse-style target data CSV."
    )
    parser.add_argument(
        "--links-file",
        type=Path,
        default=Path("source_links.txt"),
        help="Path to text file with one source URL per line.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("hubverse_observed_data.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    links = read_links(args.links_file)

    all_data: list[dict[str, object]] = []
    for url in links:
        converted = convert_single_csv(url)
        all_data.extend(converted)
        print(f"Converted {url} -> {len(converted)} rows")

    all_data.sort(
        key=lambda row: (
            str(row["target_end_date"]),
            str(row["target"]),
            str(row["location"]),
        )
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANDATORY_OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(all_data)

    print(f"Wrote {len(all_data)} rows to {args.output}")


if __name__ == "__main__":
    main()
