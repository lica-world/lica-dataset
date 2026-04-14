# LICA Dataset

A collection of 1,183 graphic design layouts with component-level specifications and natural-language annotations, released as part of the [LICA paper](https://arxiv.org/abs/2603.16098).

Each layout captures the full rendering spec of a design — positions, typography, images, background — along with annotations at both the layout and template level. Layouts are grouped by **template** (a design theme that produces multiple slide variations).

<p align="center">
<img width="800" height="500" alt="LICA dataset overview" src="https://github.com/user-attachments/assets/edee2b55-9ec9-49ac-bf3c-4bde21214f18" />
</p>

The dataset is also available on [HuggingFace](https://huggingface.co/datasets/lica-world/lica-dataset).

## Getting started

1. Download the [`lica-data`](https://storage.googleapis.com/lica-assets/websites/blog/lica-data.zip) folder and unzip it in the repo root:

```
lica-dataset/
├── lica-data/
├── lica_dataset.py
├── requirements.txt
└── README.md
```

2. Install dependencies (Python 3.9+):

```bash
pip install -r requirements.txt
```

## Dataset structure

```
lica-data/
├── metadata.csv                              # per-layout metadata
├── layouts/
│   └── <template_id>/
│       └── <layout_id>.json                  # component-level layout spec
├── images/
│   └── <template_id>/
│       └── <layout_id>.png or .mp4           # rendered layout (image or video)
└── annotations/
    ├── template_annotations.json             # template-level annotations
    └── <template_id>/
        └── <layout_id>.json                  # per-layout annotation
```

### `metadata.csv`

| Column | Type | Description |
|---|---|---|
| `layout_id` | string | Unique layout ID (matches filenames in `layouts/`, `images/`, `annotations/`) |
| `category` | string | Design category (e.g. `"Presentations"`, `"Videos"`, `"Education"`, `"Flyers"`) |
| `template_id` | string | UUID of the parent template (matches folder names) |
| `n_template_layouts` | int | Number of layouts in the template group |
| `template_layout_index` | int | Zero-based position within the template group |
| `width` | int | Canvas width in pixels |
| `height` | int | Canvas height in pixels |

### Layout JSON

Each file in `layouts/<template_id>/<layout_id>.json` contains the canvas specification and an ordered list of components:

```json
{
  "components": [ ... ],
  "background": "rgb(252, 252, 252)",
  "width": "1920px",
  "height": "1080px",
  "duration": 3
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `components` | array | yes | Ordered list of rendering components (see below) |
| `width` | string | yes | Canvas width with `"px"` suffix |
| `height` | string | yes | Canvas height with `"px"` suffix |
| `background` | string | no | CSS color for the canvas background |
| `duration` | number | no | Slide duration in seconds |

#### Component types

Each component has a `type` field and CSS-like positioning/visual properties.

**`TEXT`** — positioned text element

```json
{
  "type": "TEXT",
  "text": "Hello World",
  "left": "108px", "top": "200px", "width": "400px", "height": "50px",
  "color": "rgb(255, 255, 255)",
  "fontSize": "48px",
  "fontFamily": "League Spartan--400",
  "fontWeight": "400",
  "textAlign": "center",
  "lineHeight": "52px",
  "letterSpacing": "0em",
  "textTransform": "none",
  "fontStyle": "normal",
  "transform": "none"
}
```

**`IMAGE`** — positioned image

```json
{
  "type": "IMAGE",
  "src": "https://storage.googleapis.com/lica-video/<uuid>.png",
  "left": "0px", "top": "0px", "width": "1920px", "height": "1080px",
  "transform": "none",
  "opacity": 1,
  "overflow": "hidden"
}
```

**`GROUP`** — container/shape element with optional clip path

```json
{
  "type": "GROUP",
  "left": "108px", "top": "463px", "width": "555px", "height": "508px",
  "background": "rgb(255, 255, 255)",
  "backgroundColor": "rgb(255, 255, 255)",
  "clipPath": "path(\"M0,0 ...\")",
  "transform": "none"
}
```

### Annotations

**Per-layout** (`annotations/<template_id>/<layout_id>.json`):

```json
{
  "description": "Visual description of the specific layout",
  "aesthetics": "Notes on design style, composition, visual hierarchy",
  "tags": "comma, separated, keyword, tags",
  "user_intent": "Inferred purpose or goal of the design",
  "raw": "Concatenation of all fields above"
}
```

**Template-level** (`annotations/template_annotations.json`):

A JSON object keyed by template UUID. Each entry has the same fields (`description`, `aesthetics`, `tags`, `user_intent`, `raw`) but describes the shared design theme across all layouts in the template.

---

## Quick start

```python
from lica_dataset import LicaDataset

ds = LicaDataset("lica-data")
print(ds)
# LicaDataset(n=1183, categories=['Business Cards', 'Cards & Invitations', ...])
```

### Filtering

Filtering methods return a new `LicaDataset` view and are chainable.

```python
presentations = ds.by_category("Presentations")
template_layouts = ds.by_template("3b919d2e-539f-4b2c-8d86-7709ef65b496")
widescreen = ds.by_dimensions(1920, 1080)
portrait = ds.by_aspect_ratio("portrait")
```

### Accessing records

```python
layout_id = "gsessHF2ev5r4ZgwPUh5"

layout = ds.get_layout(layout_id)
annotation = ds.get_annotation(layout_id)
render_path = ds.get_render_path(layout_id)
meta = ds.get_metadata(layout_id)
```

### Iteration

```python
for item in ds:
    print(item["layout_id"], item["metadata"]["category"])
    # item also contains: layout, annotation, template_annotation, render_path
```

### Convenience functions

```python
from lica_dataset import (
    load_dataset,
    load_layouts_by_template,
    load_layouts_by_category,
    iter_template_groups,
)

ds = load_dataset("lica-data")
layouts = load_layouts_by_template("lica-data", "3b919d2e-539f-4b2c-8d86-7709ef65b496")

for template_id, group in iter_template_groups("lica-data"):
    print(template_id, len(group))
```

---

## API reference

### `LicaDataset(data_root)`

| Method | Description |
|---|---|
| `.by_category(category)` | Filter by design category |
| `.by_template(template_id)` | Filter by template UUID |
| `.by_dimensions(width, height)` | Filter by exact canvas dimensions |
| `.by_aspect_ratio(ratio)` | Filter by `"landscape"`, `"portrait"`, or `"square"` |
| `.get_layout(layout_id)` | Load layout JSON |
| `.get_annotation(layout_id)` | Load per-layout annotation |
| `.get_template_annotation(template_id)` | Load template-level annotation |
| `.get_render_path(layout_id)` | Path to rendered image/video (PNG or MP4) |
| `.get_metadata(layout_id)` | Single metadata row as dict |
| `.ids` | Layout IDs in current view |
| `.metadata` | Filtered metadata as DataFrame |
| `.categories` | Sorted unique categories |
| `.templates` | Unique template IDs |
| `.summary()` | Per-category summary table |

### Module-level functions

| Function | Description |
|---|---|
| `load_dataset(data_root)` | Shorthand for `LicaDataset(data_root)` |
| `load_layouts_by_template(data_root, template_id)` | Layout dicts for a template, sorted by index |
| `load_layouts_by_category(data_root, category)` | Layout dicts for a category |
| `iter_template_groups(data_root)` | Yields `(template_id, LicaDataset)` per template |

## Citation

```bibtex
@article{Hirsch2026LICA,
  title   = {LICA: Layered Image Composition Annotations for Graphic Design Research},
  author  = {Hirsch, Elad and Yadav, Shubham and Garg, Mohit and Mehta, Purvanshi},
  journal = {arXiv preprint arXiv:2603.16098},
  year    = {2026}
}
```

## License

Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
