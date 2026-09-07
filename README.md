# CanvasXpress Python Example Gallery

![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626.svg)
![CanvasXpress](https://img.shields.io/badge/CanvasXpress-Python-%234477CC.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-gray.svg?logo=github)](https://github.com/CanvasXpress/canvasxpress-examples-jupyter)

A comprehensive collection of Jupyter Notebook examples showcasing the [CanvasXpress](https://www.canvasxpress.org) Python library for creating interactive, publication-quality data visualizations.

![CanvasXpress Visualization](https://www.canvasxpress.org/assets/images/chart.png)

## Overview

This repository provides self-contained Jupyter Notebook examples demonstrating all chart types available in CanvasXpress. Each notebook is derived from the official [CanvasXpress JavaScript examples](https://www.canvasxpress.org/examples.html) and converted to use the Python API with pandas DataFrames. The examples were created using an AI-assisted workflow involving Qwen 3.6 and DeepSeek R1 to ensure accuracy and clarity.

> **Note:** These notebooks demonstrate CanvasXpress using the Python interface available on [PyPI](https://pypi.org/project/canvasxpress/).

## What's Inside

This repository includes Jupyter notebooks for **40+ chart types**, each with clear documentation and runnable code:

| Category | Chart Types |
|---|---|
| **Comparison & Ranking** | Bar, Lollipop, Dumbbell, Bullet, Dotplot, Waterfall |
| **Radial** | Radar, Circular, Meter |
| **Composition** | Stacked, StackedPercent |
| **Proportional** | Pie, Donut, Treemap, Sunburst |
| **Sets** | Venn, UpSet |
| **Distribution** | Boxplot, Violin, Histogram, Density, Ridge-Line |
| **Relationship** | Scatter2D/3D, ScatterBubble2D, 3D-Plots, Bubble |
| **2-D Density** | Contour, Hexplot-Binplot |
| **Matrix** | Correlation, SPLOM, Heatmap |
| **Model Fits** | Linear-Fit, NonLinear-Fit |
| **Trends & Time** | Line, Area, AreaLine, Streamgraph |
| **Combination** | BarLine, DotLine, StackedLine, StackedPercentLine |
| **Timelines** | Gantt, Swimmer |
| **Connections** | Sankey, Chord |
| **Tree & Network** | Tree, Network |
| **Geospatial** | Map |
| **Domain-Specific** | Genome, Oncoprint, TCGA, Kaplan-Meier, Fish |
| **Multivariate** | ParallelCoordinates, TagCloud |
| **Financial** | OptionsWall |
| **Layout** | Dashboard, Facet, Layout, Remote-Graphs, Functions |

## Quick Start

### One-Step Bootstrap (Recommended)

After cloning the repository, run the bootstrap script for your platform:

**macOS / Linux:**
```bash
./scripts/bootstrap.sh
```

**Windows:**
```bat
scripts\bootstrap.bat
```

This automates Python 3.12 installation, dependency setup, and Jupyter kernel registration.

### Manual Installation

```bash
# Clone repository
git clone https://github.com/your-username/canvasxpress-examples-jupyter.git
cd canvasxpress-examples-jupyter

# Install dependencies with uv
uv sync
```

### Running the Notebooks

```bash
# Start JupyterLab
uv run jupyter lab

# Or Jupyter Notebook (classic)
uv run jupyter notebook

# Or launch a specific notebook
uv run jupyter lab examples/bar.md
```

### Working with Markdown Source Files

Each notebook has a corresponding MyST Markdown source file, enabling easy version control and editing:

```bash
# Convert markdown to notebook
uv run jupytext --to notebook examples/bar.md

# Convert notebook to markdown
uv run jupytext --to md examples/bar.ipynb

# Sync changes between the two
uv run jupytext --sync examples/bar.md
```

## Key Features Demonstrated

The notebooks highlight CanvasXpress's unique capabilities:

- **Interactivity**: Full zoom, pan, filtering, and data point selection directly in notebooks
- **Reproducibility**: Built-in audit trail tracks all data manipulations and configurations
- **Scientific Focus**: Optimized for large-scale genomics, proteomics, and clinical datasets
- **Cross-Platform**: Works identically in JupyterLab, VS Code, Google Colab, and marimo
- **AI Integration**: Leverages natural language prompts to generate complex visualizations
- **Grammar of Graphics**: Consistent API across all chart types, similar to ggplot2

## Example: Simple Bar Chart

```python
from canvasxpress.canvas import CanvasXpress
from canvasxpress.plot import graph
import pandas as pd

df = pd.DataFrame(
    {"Var 1": [4, 5, 4, 4, 7]},
    index=pd.Index(["Cat 1", "Cat 2", "Cat 3", "Cat 4", "Cat 5"], name="Categories"),
)

cx = CanvasXpress(
    data=df,
    config={
        "graphType": "Bar",
        "title": "Bar graph with a single series",
        "xAxisTitle": "Var 1",
    },
    width=600,
    height=600,
)

graph(cx)
```

See [examples/bar.md](examples/bar.md) for the complete example with interactive visualization.

## CanvasXpress: Beyond Basic Plotting

CanvasXpress is more than a visualization library—it's a complete data exploration platform:

- **40+ Chart Types**: From simple bar charts to complex networks and genomic visualizations
- **Interactive Exploration**: Built-in filtering, sorting, clustering, and statistical operations
- **Reproducible Research**: Every chart carries its data and full configuration—share a PNG and it re-renders live
- **AI-Powered**: Describe what you want in natural language; let the built-in AI or LLM agents generate the chart
- **Scientific-Grade**: Handles millions of data points with HTML5 Canvas performance
- **Cross-Language**: Same grammar in Python, R, and JavaScript

Learn more at [canvasxpress.org](https://www.canvasxpress.org) or explore the [full example gallery](https://www.canvasxpress.org/examples.html).

## How This Project Was Built

This repository was created using a novel AI-assisted workflow:

### AI Agents Used
- **Qwen 3.6-35B** (primary coding agent) — generated Python code, notebooks, and prompts
- **DeepSeek-R1-Distill-Qwen-7B** (user-proxy) — simulated scientist/student prompts for iterative refinement

### Agent Skills
The project leverages the [CanvasXpress Python agent skills](https://github.com/CanvasXpress/canvasxpress-python) which provide:
- Specialized knowledge of the CanvasXpress Python API
- Chart type recommendations based on data characteristics
- Production-ready configuration patterns
- Integration guidance for Jupyter, Dash, Shiny, and Streamlit

### The Workflow
1. Inspect the original CanvasXpress JavaScript example from [canvasxpress.org](https://www.canvasxpress.org)
2. Create a MyST Markdown notebook with title, description, data, and configuration
3. Use DeepSeek to simulate how a scientist would describe the desired chart in plain English
4. Iterate on the prompt until it produces code matching the target CanvasXpress output
5. Convert the Markdown to a Jupyter Notebook using Jupytext

See `skills/notebook-from-example.md` for the complete workflow documentation.

## Dependencies

All notebooks use the same Python kernel and dependencies:

| Package | Purpose |
|---|---|
| [canvasxpress](https://pypi.org/project/canvasxpress/) | Interactive visualization library |
| pandas | Data manipulation and DataFrame handling |
| jupyterlab | Interactive notebook environment |
| jupytext | Markdown↔Notebook conversion |
| ipywidgets | Interactive Jupyter components |

## CanvasXpress Origins

**CanvasXpress** was originally created by **Dr. Isaac Neuhaus**, a computational biologist and visualization expert based in Pennington, New Jersey. Dr. Neuhaus developed CanvasXpress as the core visualization component for bioinformatics and systems biology analysis, and it has since grown into a comprehensive data analytics platform used by researchers worldwide.

Dr. Neuhaus actively maintains the JavaScript, PHP, and R editions of CanvasXpress (available on [CRAN](https://cran.r-project.org/web/packages/canvasXpress/index.html)), and provides significant technical guidance for the Python edition. His recent work includes:

- Re-engineering CanvasXpress as a full **Extended Grammar of Graphics** with ggplot2-like semantics
- Integrating **LLM-powered visualization generation** with guided autocomplete (published in the [Journal of Open Source Software](https://joss.theoj.org/))
- Developing the **Model Context Protocol (MCP)** server for AI agent integration
- Publishing research on Sankey diagrams, Chord diagrams, and interactive Jupyter visualizations

Learn more about Dr. Neuhaus:
- [GitHub: neuhausi/canvasXpress](https://github.com/neuhausi/canvasxpress)
- [LinkedIn: Isaac Neuhaus](https://www.linkedin.com/in/isaac-neuhaus-3b3ab5/)
- [canvasxpress.org](https://www.canvasxpress.org)

## Author

This repository of Python example notebooks is created and maintained by **Dr. Todd C. Brett**, author of [canvasxpress-python](https://github.com/CanvasXpress/canvasxpress-python). Dr. Brett works closely with Dr. Neuhaus to ensure the Python library maintains feature parity with the JavaScript and R editions while leveraging Python's data science ecosystem.

Questions, comments, and contributions are welcome! Please feel free to:

- [Open an issue](https://github.com/CanvasXpress/canvasxpress-examples-jupyter/issues)
- Submit a pull request with new examples
- Star this repository if you find it useful

---

*Built with ❤️ using CanvasXpress, Qwen 3.6, and DeepSeek R1*
