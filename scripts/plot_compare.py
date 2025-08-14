#!/usr/bin/env python3
"""
Generate a grid of bar charts comparing hydrological estimates per site.

- Reads data from a semicolon-separated CSV at `src/api/compare.csv` by default.
- Expects columns like: ID, Name, Measured, MF, Koella, Clark-WSL, [Scherrer|SCS-NAM], Classification (some may be missing/unnamed).
- Produces a multi-subplot figure similar to the sample image provided, with one
  subplot per site and bars for the available methods.

Usage:
    python scripts/plot_compare.py \
        --csv-path src/api/compare.csv \
        --output build/compare_grid.png \
        --ncols 5 \
        --dpi 200

The script is defensive against slightly inconsistent headers (e.g., unnamed
columns). It will display `SCS-NAM` as `Scherrer` for labels to match the image.
"""

from __future__ import annotations

import argparse
import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_METHOD_ORDER: List[str] = [
    "MF",
    "Koella",
    "Clark-WSL",
    "Scherrer",  # mapped from 'Measured' column when present
    "SCS-NAM",
]


def _coerce_float(value: object) -> Optional[float]:
    """Attempt to coerce a value to float; return None if not possible."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value
    try:
        txt = str(value).strip().replace(" ", "")
        if txt == "" or txt.lower() == "nan":
            return None
        return float(txt)
    except Exception:
        return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and clean column names; drop entirely empty columns.

    - Strip whitespace from column names
    - Replace empty/unnamed columns with a generated name
    - Drop columns that are entirely empty (NaN/blank strings)
    """
    new_columns: List[str] = []
    for idx, col in enumerate(df.columns):
        name = str(col).strip()
        if name == "" or name.startswith("Unnamed"):
            # Leave a placeholder name so we can inspect contents
            name = f"_unnamed_{idx}"
        new_columns.append(name)
    df = df.copy()
    df.columns = new_columns

    # Drop completely empty columns (all NaN or blank strings)
    drop_cols: List[str] = []
    for col in df.columns:
        series = df[col]
        # Consider blank strings as missing
        is_missing = series.isna() | (series.astype(str).str.strip() == "")
        if is_missing.all():
            drop_cols.append(col)
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # Attempt to rename commonly unnamed columns
    # If we find a column with textual categories and no header, treat as Classification
    for col in list(df.columns):
        if col.startswith("_unnamed_"):
            # Heuristic: if the column looks numeric, it might actually be a method column with missing header
            sample_values = df[col].dropna().astype(str).str.strip()
            looks_numeric = sample_values.sample(n=min(5, len(sample_values)), random_state=0).str.match(r"^[+-]?\d+(?:\.\d+)?$").all() if not sample_values.empty else False
            if looks_numeric:
                # Keep as-is; the plotting routine will ignore unknown method names
                continue
            # Otherwise, assume it's the classification/notes column
            df = df.rename(columns={col: "Classification"})

    # If SCS-NAM exists, keep it; we will display it as Scherrer by default
    return df


def read_compare_csv(csv_path: str) -> pd.DataFrame:
    """Read the semicolon-separated compare CSV and return a cleaned DataFrame."""
    df = pd.read_csv(csv_path, sep=";", engine="python")
    df = _normalize_columns(df)
    return df


def determine_methods(df: pd.DataFrame, preferred_order: Sequence[str]) -> List[Tuple[str, str]]:
    """Return list of (canonical_method_name, column_name) in desired order.

    The canonical method 'Scherrer' maps to the 'Measured' column if present,
    falling back to a literal 'Scherrer' column if available.
    """
    lower_to_original: Dict[str, str] = {str(c).strip().lower(): str(c) for c in df.columns}

    chosen_columns: set = set()
    results: List[Tuple[str, str]] = []

    for method in preferred_order:
        method_lower = method.lower()
        column_name: Optional[str] = None

        if method == "Scherrer":
            if "measured" in lower_to_original:
                column_name = lower_to_original["measured"]
            elif "scherrer" in lower_to_original:
                column_name = lower_to_original["scherrer"]
        else:
            if method_lower in lower_to_original:
                column_name = lower_to_original[method_lower]

        if column_name and column_name not in chosen_columns:
            results.append((method, column_name))
            chosen_columns.add(column_name)

    return results


def format_value_label(value: float) -> str:
    """Format numeric labels displayed above bars."""
    if value is None:
        return ""
    if value < 10:
        return f"{value:.1f}"
    return f"{value:.1f}"


def plot_compare(
    df: pd.DataFrame,
    output_path: str,
    ncols: int = 5,
    dpi: int = 200,
    title: str = "Comparison of HQ100",
    display_label_overrides: Optional[Dict[str, str]] = None,
) -> None:
    methods = determine_methods(df, DEFAULT_METHOD_ORDER)
    if not methods:
        raise ValueError("No method columns found in the CSV. Expected one of: " + ", ".join(DEFAULT_METHOD_ORDER))

    # Ensure essential columns exist
    name_col_candidates = [c for c in df.columns if str(c).strip().lower() == "name"]
    if not name_col_candidates:
        raise ValueError("CSV must contain a 'Name' column.")
    name_col = name_col_candidates[0]

    num_sites = len(df)
    nrows = int(math.ceil(num_sites / float(ncols)))

    fig_width = max(8, ncols * 4)
    fig_height = max(6, nrows * 3.2)
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(fig_width, fig_height), dpi=dpi)
    # Normalize to a flat list of Axes for simple indexing regardless of shape
    if isinstance(axes, plt.Axes):
        axes_list: List[plt.Axes] = [axes]
    else:
        # `axes` is a numpy ndarray when nrows*ncols > 1
        axes_list = list(axes.ravel().tolist())  # type: ignore[attr-defined]

    color_map = {
        "MF": "#4e79a7",  # blue
        "Koella": "#f28e2c",  # orange
        "Clark-WSL": "#59a14f",  # green
        "Scherrer": "#76b7b2",  # teal
        "SCS-NAM": "#af7aa1",  # purple
    }

    label_overrides = display_label_overrides or {}

    for idx, (_, row) in enumerate(df.iterrows()):
        ax = axes_list[idx]
        site_name = str(row[name_col])

        x_labels: List[str] = []
        y_values: List[float] = []
        bar_colors: List[str] = []

        for canonical_name, column_name in methods:
            raw_value = row.get(column_name, None)
            value = _coerce_float(raw_value)
            if value is None:
                continue
            display_label = label_overrides.get(canonical_name, canonical_name)
            x_labels.append(display_label)
            y_values.append(value)
            bar_colors.append(color_map.get(canonical_name, "#9e9e9e"))

        # Draw bars
        x_positions = range(len(x_labels))
        bars = ax.bar(list(x_positions), y_values, color=bar_colors, width=0.6)

        # Label bars
        for bar, value in zip(bars, y_values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (0.03 * max(1.0, max(y_values) if y_values else 1.0)),
                format_value_label(value),
                ha="center",
                va="bottom",
                fontsize=8,
            )

        ax.set_xticks(list(x_positions), x_labels, fontsize=8)
        ax.set_title(site_name, fontsize=10)
        ax.grid(axis="y", linestyle=":", linewidth=0.6, alpha=0.6)

        # Y label only on the first column
        if (idx % ncols) == 0:
            ax.set_ylabel("HQ100 [m³/s]")

        # Set y-limits with a small headroom
        if y_values:
            ymax = max(y_values)
            ax.set_ylim(0, ymax * 1.25 + 0.1)
        else:
            ax.set_ylim(0, 1)

    # Hide any unused axes
    for j in range(num_sites, len(axes_list)):
        axes_list[j].axis("off")

    fig.suptitle(title, fontsize=14, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.98))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path)
    print(f"Saved figure to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create comparison bar chart grid from CSV")
    parser.add_argument(
        "--csv-path",
        default=os.path.join(os.path.dirname(__file__), "compare.csv"),
        help="Path to the semicolon-separated input CSV",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("build", "compare_grid.png"),
        help="Path to save the generated PNG",
    )
    parser.add_argument(
        "--ncols",
        type=int,
        default=5,
        help="Number of columns in the subplot grid",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="DPI for the output figure",
    )
    parser.add_argument(
        "--title",
        default="Comparison of HQ100",
        help="Figure title",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = read_compare_csv(args.csv_path)
    plot_compare(
        df=df,
        output_path=args.output,
        ncols=args.ncols,
        dpi=args.dpi,
        title=args.title,
    )


if __name__ == "__main__":
    main()


