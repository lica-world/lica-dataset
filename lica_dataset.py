"""Python helpers for loading and filtering the LICA layout dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pandas as pd


class LicaDataset:
    """Pandas-backed interface over the LICA layout dataset with chainable filters."""

    def __init__(self, data_root: str | Path) -> None:
        self._root = Path(data_root)
        self._meta: pd.DataFrame = self._load_metadata()
        self._template_annotations: dict[str, dict] = self._load_template_annotations()

    def _load_metadata(self) -> pd.DataFrame:
        csv_path = self._root / "metadata.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"metadata.csv not found at {csv_path}")
        df = pd.read_csv(csv_path, dtype=str)
        for col in ("n_template_layouts", "template_layout_index", "width", "height"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.reset_index(drop=True)

    def _load_template_annotations(self) -> dict[str, dict]:
        ann_path = self._root / "annotations" / "template_annotations.json"
        if not ann_path.exists():
            return {}
        with ann_path.open(encoding="utf-8") as fh:
            return json.load(fh)

    @classmethod
    def _from_state(
        cls,
        root: Path,
        meta: pd.DataFrame,
        template_annotations: dict[str, dict],
    ) -> LicaDataset:
        """Create a filtered view without reloading from disk."""
        obj = cls.__new__(cls)
        obj._root = root
        obj._meta = meta.reset_index(drop=True)
        obj._template_annotations = template_annotations
        return obj

    def _filter(self, mask: pd.Series) -> LicaDataset:
        return LicaDataset._from_state(
            self._root, self._meta[mask], self._template_annotations
        )

    def _resolve_template_id(self, layout_id: str) -> str:
        row = self._meta[self._meta["layout_id"] == layout_id]
        if row.empty:
            raise KeyError(
                f"layout_id {layout_id!r} not found in current view. "
                "Use the full dataset if filtering has excluded it."
            )
        return row.iloc[0]["template_id"]

    def by_category(self, category: str) -> LicaDataset:
        """Filter by design category (case-sensitive)."""
        return self._filter(self._meta["category"] == category)

    def by_template(self, template_id: str) -> LicaDataset:
        """Return all layouts belonging to the given template."""
        return self._filter(self._meta["template_id"] == template_id)

    def by_dimensions(self, width: int, height: int) -> LicaDataset:
        """Filter layouts matching exact canvas dimensions (in pixels)."""
        mask = (self._meta["width"] == width) & (self._meta["height"] == height)
        return self._filter(mask)

    def by_aspect_ratio(self, ratio: str) -> LicaDataset:
        """Filter by aspect ratio: 'landscape', 'portrait', or 'square'."""
        w = self._meta["width"]
        h = self._meta["height"]
        if ratio == "landscape":
            return self._filter(w > h)
        if ratio == "portrait":
            return self._filter(h > w)
        if ratio == "square":
            return self._filter(w == h)
        raise ValueError(
            f"Unknown ratio '{ratio}'. Choose from 'landscape', 'portrait', 'square'."
        )

    def get_layout(self, layout_id: str) -> dict:
        """Load and return the layout JSON for a given layout ID."""
        template_id = self._resolve_template_id(layout_id)
        path = self._root / "layouts" / template_id / f"{layout_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Layout JSON not found: {path}")
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def get_annotation(self, layout_id: str) -> dict:
        """Load the per-layout annotation (description, aesthetics, tags, user_intent)."""
        template_id = self._resolve_template_id(layout_id)
        path = self._root / "annotations" / template_id / f"{layout_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Annotation not found: {path}")
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def get_template_annotation(self, template_id: str) -> dict:
        """Return the template-level annotation for a template UUID."""
        if template_id not in self._template_annotations:
            raise KeyError(
                f"No template annotation found for: {template_id!r}"
            )
        return self._template_annotations[template_id]

    def get_render_path(self, layout_id: str) -> Path:
        """Return the path to the rendered image/video (.png preferred, then .mp4)."""
        template_id = self._resolve_template_id(layout_id)
        base = self._root / "images" / template_id / layout_id
        png = base.with_suffix(".png")
        if png.exists():
            return png
        mp4 = base.with_suffix(".mp4")
        if mp4.exists():
            return mp4
        return png

    def get_image_path(self, layout_id: str) -> Path:
        """Alias for get_render_path."""
        return self.get_render_path(layout_id)

    def get_metadata(self, layout_id: str) -> dict:
        """Return a single metadata row as a dict."""
        row = self._meta[self._meta["layout_id"] == layout_id]
        if row.empty:
            raise KeyError(
                f"layout_id {layout_id!r} not found in current view. "
                "Use the full dataset if filtering has excluded it."
            )
        return row.iloc[0].to_dict()

    def __len__(self) -> int:
        return len(self._meta)

    def __iter__(self) -> Iterator[dict]:
        for idx in range(len(self)):
            yield self[idx]

    def __getitem__(self, idx: int) -> dict:
        if idx < 0 or idx >= len(self._meta):
            raise IndexError(
                f"Index {idx} out of range for dataset of size {len(self._meta)}."
            )
        row = self._meta.iloc[idx]
        layout_id: str = row["layout_id"]
        template_id: str = row["template_id"]

        # Lazily load layout — only if the file exists on disk
        layout_path = self._root / "layouts" / template_id / f"{layout_id}.json"
        layout = None
        if layout_path.exists():
            with layout_path.open(encoding="utf-8") as fh:
                layout = json.load(fh)

        # Lazily load annotation
        ann_path = self._root / "annotations" / template_id / f"{layout_id}.json"
        annotation = None
        if ann_path.exists():
            with ann_path.open(encoding="utf-8") as fh:
                annotation = json.load(fh)

        # Resolve render path (PNG or MP4)
        base = self._root / "images" / template_id / layout_id
        render = base.with_suffix(".png")
        if not render.exists():
            mp4 = base.with_suffix(".mp4")
            if mp4.exists():
                render = mp4

        return {
            "layout_id": layout_id,
            "template_id": template_id,
            "metadata": row.to_dict(),
            "layout": layout,
            "annotation": annotation,
            "template_annotation": self._template_annotations.get(template_id),
            "render_path": render,
            "image_path": render,
        }

    @property
    def ids(self) -> list[str]:
        return self._meta["layout_id"].tolist()

    @property
    def metadata(self) -> pd.DataFrame:
        return self._meta.copy()

    @property
    def categories(self) -> list[str]:
        return sorted(self._meta["category"].dropna().unique().tolist())

    @property
    def templates(self) -> list[str]:
        return self._meta["template_id"].dropna().unique().tolist()

    def __repr__(self) -> str:
        return (
            f"LicaDataset("
            f"n={len(self)}, "
            f"categories={self.categories}"
            f")"
        )

    def summary(self) -> pd.DataFrame:
        """Per-category summary: layout count, template count, dimensions."""
        grouped = (
            self._meta.groupby("category", sort=True)
            .agg(
                n_layouts=("layout_id", "count"),
                n_templates=("template_id", "nunique"),
                dimensions=(
                    "width",
                    lambda x: sorted(
                        set(
                            zip(
                                x.values,
                                self._meta.loc[x.index, "height"].values,
                            )
                        )
                    ),
                ),
            )
            .reset_index()
        )
        return grouped


def load_dataset(data_root: str | Path = "lica-data") -> LicaDataset:
    """Shorthand for ``LicaDataset(data_root)``."""
    return LicaDataset(data_root)


def load_layouts_by_template(
    data_root: str | Path,
    template_id: str,
) -> list[dict]:
    """Load all layout dicts for a template, sorted by template_layout_index."""
    ds = LicaDataset(data_root).by_template(template_id)
    ordered = ds.metadata.sort_values("template_layout_index")
    return [ds.get_layout(lid) for lid in ordered["layout_id"]]


def load_layouts_by_category(
    data_root: str | Path,
    category: str,
) -> list[dict]:
    """Load all layout dicts for a category (skips missing files)."""
    ds = LicaDataset(data_root).by_category(category)
    layouts = []
    for lid in ds.ids:
        try:
            layouts.append(ds.get_layout(lid))
        except FileNotFoundError:
            continue
    return layouts


def iter_template_groups(
    data_root: str | Path,
) -> Iterator[tuple[str, LicaDataset]]:
    """Yield ``(template_id, LicaDataset)`` for each template group."""
    ds = LicaDataset(data_root)
    for tid in ds.templates:
        group = ds.by_template(tid)
        sorted_meta = group.metadata.sort_values("template_layout_index")
        yield tid, LicaDataset._from_state(
            group._root,
            sorted_meta,
            group._template_annotations,
        )
