"""
Tasks for generating and refining agent prompts for CanvasXpress examples.

Uses DeepSeek LLM to analyze chart data/config and generate improved
agent prompts that accurately describe what the chart shows.

Usage:
    invoke prompt.generate --example 17 --file examples/bar.md
    invoke prompt.evaluate --example 17 --file examples/bar.md
    invoke prompt.refine --example 17 --file examples/bar.md --iterations 5
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from invoke import context, task

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

API_URL = "http://127.0.0.1:8000/v1/chat/completions"
API_KEY = os.getenv("API_KEY")
DEEPSEEK_MODEL = "DeepSeek-R1-Distill-Qwen-7B-4bit"
QWEN_MODEL = "Qwen3.6-35B-A3B-OptiQ-4bit"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def py_to_json(s: str) -> str:
    """Convert Python True/False/None to JSON true/false/null."""
    return s.replace("True", "true").replace("False", "false").replace("None", "null")


def _extract_json_from_response(response: str) -> dict | None:
    """Extract the outermost JSON object from a response that may contain reasoning text."""
    # Find the first '{' and last '}'
    first_brace = response.find("{")
    last_brace = response.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
        return None

    candidate = response[first_brace : last_brace + 1]

    # Verify it's valid JSON by checking brace matching
    depth = 0
    in_string = False
    escaped = False
    for char in candidate:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and not escaped:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                break

    if depth != 0:
        return None

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def call_llm(
    messages: list[dict], max_tokens: int = 4096, model: str = DEEPSEEK_MODEL
) -> str:
    """Call the local LLM API."""
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def _fetch_html(url: str) -> str:
    """Fetch a URL and return the HTML content."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def _download_txt(url: str) -> str:
    """Download a TSV text file from CanvasXpress data server."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def _parse_tsv_to_dict(tsv: str) -> dict:
    """Parse a CanvasXpress TSV file to a dict with y/x keys.

    Example TSV:
    S1  S2  S3
    V1  10  15  20

    Returns: {"y": {"vars": ["V1"], "smps": ["S1","S2","S3"], "data": [[10,15,20]]}}
    """
    lines = tsv.strip().split("\n")
    if len(lines) < 2:
        return {"y": {"vars": [], "smps": [], "data": []}}

    # First line is sample IDs
    smps = lines[0].split("\t")
    smps = [s.strip() for s in smps if s.strip()]

    # Remaining lines are variables
    vars_list = []
    data = []
    for line in lines[1:]:
        parts = line.split("\t")
        if not parts[0].strip():
            continue
        var_name = parts[0].strip()
        values = [float(v) if v.strip() else 0 for v in parts[1:] if v.strip()]
        vars_list.append(var_name)
        data.append(values)

    return {"y": {"vars": vars_list, "smps": smps, "data": data}}


def _fetch_lollipop_example_data(example_num: int) -> tuple[dict, dict]:
    """Fetch lollipop example data from CanvasXpress data files.

    Returns (data_dict, config_dict).
    """
    # Data file URL pattern
    if example_num == 1:
        data_url = "https://www.canvasxpress.org/data/r/cX-lollipop-dat.txt"
    elif example_num == 2:
        data_url = "https://www.canvasxpress.org/data/r/cX-lollipop2-dat.txt"
    else:
        return {}, {}

    tsv = _download_txt(data_url)
    data = _parse_tsv_to_dict(tsv)

    # Config for lollipop
    if example_num == 1:
        config = {
            "barType": "lollipop",
            "colorScheme": "CanvasXpress",
            "dataPointSizeScaleFactor": 6,
            "graphType": "Bar",
            "widthFactor": 0.2,
            "sizeBy": "val",
            "xAxis": ["V1"],
        }
    elif example_num == 2:
        config = {
            "barLollipopOpen": True,
            "barType": "lollipopBullet",
            "colorScheme": "GGPlot",
            "dataPointSizeScaleFactor": 7,
            "graphType": "Bar",
            "marginBottom": 50,
            "marginLeft": 50,
            "marginRight": 50,
            "marginTop": 50,
            "maxTextSize": 80,
            "rangeColors": ["rgb(200,200,200)"],
            "setMaxX": 150,
            "setMinX": -150,
            "showDataValues": True,
            "showLegend": False,
            "title": "Occupations",
            "xAxis": ["Var1"],
            "xAxis2Show": False,
            "xAxisGridMajorShow": False,
            "xAxisGridMinorShow": False,
            "xAxisShow": False,
        }
    else:
        config = {}

    return data, config


def _extract_data_and_config_from_html(html: str) -> tuple[dict, dict | None]:
    """Extract JS data/config from CanvasXpress HTML directly.

    CanvasXpress embeds code in <html> blocks. We extract directly using regex
    since the JS format is predictable. No DeepSeek needed for extraction.

    Returns (data_dict, config_dict) where data_dict is always a proper dict.
    """

    def _extract_js_object(text: str, var_name: str) -> str | None:
        """Extract a JS object variable value handling nested braces."""
        pattern = re.compile(rf"{re.escape(var_name)}\s*=\s*([{{].*?);", re.DOTALL)
        match = pattern.search(text)
        if not match:
            return None
        value = match.group(1)
        # Find matching closing brace
        depth = 0
        for i, char in enumerate(value):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return value[: i + 1]
        return None

    # Extract <html> blocks
    html_blocks = re.findall(r"<html>(.*?)</html>", html, re.DOTALL)

    best_data = {}
    best_config = None

    for block in html_blocks[:2]:
        # Find config variable
        config_raw = _extract_js_object(block, "var config")
        if not config_raw:
            continue

        config_json = py_to_json(config_raw)
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError:
            continue

        # Find ALL data variable matches (handle nested braces)
        data_matches = list(re.finditer(r"var data\s*=", block, re.DOTALL))

        for dm in data_matches:
            # Extract the value after "var data ="
            after = block[dm.end() :]
            if after.lstrip().startswith("{"):
                # Extract balanced object from after text
                stripped = after.lstrip()
                depth = 0
                for j, char in enumerate(stripped):
                    if char == "{":
                        depth += 1
                    elif char == "}":
                        depth -= 1
                        if depth == 0:
                            data_raw = stripped[: j + 1]
                            data_json = py_to_json(data_raw)
                            try:
                                data = json.loads(data_json)
                                if "y" in data and "x" in data:
                                    return data, config
                                if "y" in data and (
                                    "x" not in best_data or not best_data.get("y")
                                ):
                                    best_data, best_config = data, config
                            except json.JSONDecodeError:
                                pass
                            break
            elif after.lstrip().startswith("["):
                # Extract array value (simpler, no nested braces to worry about)
                arr_match = re.match(r"\s*\[(.*?)\];", after, re.DOTALL)
                if arr_match:
                    data_raw = arr_match.group(1).strip()
                    data = _convert_2d_array_to_xyz(data_raw)
                    if not best_data:
                        best_data, best_config = data, config

        # Special handling for network charts (edges/nodes/groups data format)
        if not best_data or (
            "y" not in best_data and "edges" in str(best_data).lower()
        ):
            # Look for var data = { ... } with edges
            network_data_match = re.search(r"var data\s*=\s*({)", block)
            if network_data_match:
                start = network_data_match.start() + len("var data = ")
                # Find the opening brace
                brace_start = block.find("{", start)
                if brace_start != -1:
                    # Extract balanced braces
                    depth = 0
                    for i, char in enumerate(block[brace_start:]):
                        if char == "{":
                            depth += 1
                        elif char == "}":
                            depth -= 1
                            if depth == 0:
                                data_raw = block[brace_start : brace_start + i + 1]
                                data_raw = (
                                    data_raw.replace("'", '"')
                                    .replace("true", "true")
                                    .replace("false", "false")
                                    .replace("null", "null")
                                )
                                try:
                                    data = json.loads(data_raw)
                                    if "edges" in data:
                                        best_data = data
                                        best_config = config
                                except json.JSONDecodeError:
                                    pass
                                break

        # Special handling for venn charts
        if not best_data or ("y" not in best_data and "venn" in str(best_data).lower()):
            venn_data_match = re.search(r"var data\s*=\s*({)", block)
            if venn_data_match:
                start = venn_data_match.start() + len("var data = ")
                brace_start = block.find("{", start)
                if brace_start != -1:
                    depth = 0
                    for i, char in enumerate(block[brace_start:]):
                        if char == "{":
                            depth += 1
                        elif char == "}":
                            depth -= 1
                            if depth == 0:
                                data_raw = block[brace_start : brace_start + i + 1]
                                if '"venn"' in data_raw or '"vennData"' in data_raw:
                                    data_raw = (
                                        data_raw.replace("'", '"')
                                        .replace("true", "true")
                                        .replace("false", "false")
                                        .replace("null", "null")
                                    )
                                    try:
                                        data = json.loads(data_raw)
                                        if "venn" in data or "vennData" in data:
                                            best_data = data
                                            best_config = config
                                    except json.JSONDecodeError:
                                        pass
                                break

    return best_data, best_config


def _convert_2d_array_to_xyz(df_str: str) -> dict:
    """Convert a JS-style 2D array DataFrame to CanvasXpress XYZ dict.

    Handles: [["Id","V1","Color"], ["S1",10,"A"], ["S2",20,"B"], ...]
    Returns: {"y": {"vars": ["V1","Color"], "smps": ["S1","S2",...], "data": [[10,"A"],[20,"B"]]}, "x": {...}}
    """
    # Clean up the JS array syntax
    df_str = df_str.strip()
    if df_str.startswith("["):
        df_str = df_str[1:]
    if df_str.endswith("]"):
        df_str = df_str[:-1]

    # Split into rows
    rows = []
    current_row = ""
    depth = 0
    for char in df_str:
        if char == "[":
            depth += 1
            current_row += char
        elif char == "]":
            depth -= 1
            current_row += char
        elif char == "," and depth == 0:
            rows.append(current_row.strip())
            current_row = ""
        else:
            current_row += char
    if current_row.strip():
        rows.append(current_row.strip())

    if not rows:
        return {"y": {"vars": [], "smps": [], "data": []}}

    # First row is header
    header = _parse_array_row(rows[0])

    # Remaining rows are data
    smps = []
    y_data = []
    x_data: dict[str, list] = {}

    # Check if first data row has 3+ columns (indicating potential x annotations)
    # Only treat columns 3+ as x annotations if the array looks like it has annotations
    # (i.e., column 3 contains strings like "A", "B", "C" rather than numbers)
    first_data_row = None
    for row_str in rows[1:]:
        if row_str.strip():
            first_data_row = _parse_array_row(row_str)
            break

    has_annotations = False
    num_x_cols = 0
    if first_data_row and len(first_data_row) > 2:
        # Check if column 3 looks like annotation data (string values)
        col3_val = first_data_row[2]
        if (
            isinstance(col3_val, str)
            and not col3_val.replace(".", "").replace("-", "").isdigit()
        ):
            has_annotations = True
            num_x_cols = len(first_data_row) - 2

    for row_str in rows[1:]:
        if not row_str.strip():
            continue
        parts = _parse_array_row(row_str)
        if not parts:
            continue

        smps.append(parts[0])

        # y_values are columns 2 through end (or columns 2 to (2+num_y_cols-1) if has annotations)
        if has_annotations:
            num_y_cols = len(parts) - 1 - num_x_cols
            y_values = []
            for j in range(num_y_cols):
                if j + 1 < len(parts):
                    y_values.append(_convert_value(parts[j + 1]))
            y_data.append(y_values)

            # Build x data for annotations (columns 3+)
            for j in range(num_x_cols):
                col_idx = 2 + j
                if col_idx < len(parts):
                    var_name = (
                        header[col_idx]
                        if col_idx < len(header)
                        else f"Var{col_idx + 1}"
                    )
                    if var_name not in x_data:
                        x_data[var_name] = []
                    x_data[var_name].append(_convert_value(parts[col_idx]))
        else:
            # All columns after first are y data
            y_values = [_convert_value(p) for p in parts[1:]]
            y_data.append(y_values)

    # Vars are columns 2+ excluding columns that are in x_data
    all_var_names = [header[j] for j in range(1, len(header)) if j < len(header)]
    x_var_names = list(x_data.keys())
    vars = [v for v in all_var_names if v not in x_var_names]
    if not vars:
        vars = (
            [f"Var{i}" for i in range(1, len(parts) - len(x_data) + 1)] if parts else []
        )
    y_dict = {"vars": vars, "smps": smps, "data": y_data}

    result = {"y": y_dict}
    if x_data:
        result["x"] = x_data

    return result


def _parse_array_row(row_str: str) -> list[str]:
    """Parse a JS array row like '["S1",10,"A"]' into list of values."""
    row_str = row_str.strip().strip("[").strip("]").strip(",")
    if not row_str:
        return []

    parts = []
    current = ""
    in_quotes = False
    for char in row_str:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char == "," and not in_quotes:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())

    # Clean up quotes and brackets from values
    result = []
    for p in parts:
        p = p.strip().strip("[]")
        if p.startswith('"') and p.endswith('"'):
            p = p[1:-1]
        elif p.startswith("'") and p.endswith("'"):
            p = p[1:-1]
        result.append(p)
    return result


def _convert_value(s: str):
    """Convert a string value to appropriate Python type."""
    s = s.strip().strip('"').strip("'")
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() == "null" or s == "":
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _is_simple_value(v) -> bool:
    """Check if a value is a simple type (not nested dict/list)."""
    return isinstance(v, (str, int, float, bool)) or v is None


def _dict_to_python_code(obj, indent: int = 2, level: int = 0) -> str:
    """Convert a Python dict/list to source code string.

    Handles nested dicts, lists, strings, numbers, booleans, None.
    Uses Python syntax (True/False/None, single-quoted strings).
    Simple lists are formatted on a single line.
    """
    prefix = " " * (indent * level)
    inner_prefix = " " * (indent * (level + 1))

    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = []
        for k, v in obj.items():
            val_str = _dict_to_python_code(v, indent, level + 1)
            items.append(f"{inner_prefix}{k!r}: {val_str},")
        return "{\n" + "\n".join(items) + f"\n{prefix}}}"
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        # Check if all items are simple values (no nested structures)
        if all(_is_simple_value(v) for v in obj):
            items = []
            for v in obj:
                items.append(_dict_to_python_code(v, indent, level))
            return f"[{', '.join(items)}]"
        items = []
        for v in obj:
            val_str = _dict_to_python_code(v, indent, level + 1)
            items.append(f"{inner_prefix}{val_str},")
        return "[\n" + "\n".join(items) + f"\n{prefix}]"
    elif isinstance(obj, bool):
        return "True" if obj else "False"
    elif obj is None:
        return "None"
    elif isinstance(obj, str):
        return repr(obj)  # Single-quoted string
    elif isinstance(obj, (int, float)):
        return str(obj)
    else:
        return repr(obj)


# ---------------------------------------------------------------------------
# Existing prompt generation functions (keep these)
# ---------------------------------------------------------------------------


def extract_example(filepath: Path, example_number: int) -> tuple[dict, dict, str]:
    """Extract data dict, config dict, and raw code from an example block."""
    text = filepath.read_text()
    # Two-step approach: find the code-cell marker after the Example header,
    # then find the matching closing ```
    header = f"## Example {example_number}"
    header_idx = text.find(header)
    if header_idx == -1:
        raise ValueError(f"Could not find {header} in {filepath}")

    code_start = text.find("```{code-cell} ipython3", header_idx)
    if code_start == -1:
        raise ValueError(
            f"Could not find code cell for Example {example_number} in {filepath}"
        )

    code_start += len("```{code-cell} ipython3\n")
    end_pos = text.find("\n```", code_start)
    if end_pos == -1:
        raise ValueError(
            f"Could not find end of code cell for Example {example_number}"
        )

    code = text[code_start:end_pos].strip()

    data_raw = re.search(r"data = (.*?)\n\nconfig", code, re.DOTALL).group(1)
    config_raw = re.search(
        r"config = (.*?)\s*\n\s*cx = CanvasXpress", code, re.DOTALL
    ).group(1)

    data = json.loads(py_to_json(data_raw))
    config = json.loads(py_to_json(config_raw))

    return data, config, code


def _error_bar_summary(config: dict) -> str:
    """Build a human-readable error-bar summary from config."""
    errors = config.get("decorations", {}).get("error", [])
    if not errors:
        return ""
    samples = list({e.get("sample", "") for e in errors})
    count = len(errors)
    return (
        f"\n\nError bars: {count} decorations across samples "
        f"{', '.join(samples)}. Each error bar specifies a min/max range "
        f"per gene scope (e.g. 'HvHvOSCA1.1')."
    )


def _data_summary(data: dict) -> dict:
    """Condensed data info for prompts."""
    return {
        "vars": data["y"]["vars"],
        "num_samples": len(data["y"]["smps"]),
        "first_5_smps": data["y"]["smps"][:5],
    }


def _build_system_prompt() -> dict:
    return {
        "role": "system",
        "content": (
            "You are a scientific data visualization expert. Describe charts "
            "in plain English that a biologist or chemist would use. Focus on "
            "what the data shows, not how it is coded. DO NOT include any "
            "Python code, JSON, or configuration syntax in your response."
        ),
    }


def build_initial_prompt(data: dict, config: dict, data_info: dict) -> str:
    """Build the first (cold) prompt for DeepSeek."""
    err_summary = _error_bar_summary(config)
    color_info = _color_key_summary(config)

    return f"""\
Based on the following CanvasXpress chart definition, describe what this
chart shows in plain English, as if you were a scientist explaining results
to a colleague.

## DATA SUMMARY
- Variables (conditions): {", ".join(data_info["vars"])}
- Total samples: {data_info["num_samples"]} (first 5: {", ".join(data_info["first_5_smps"])})
{color_info}

## CHART CONFIGURATION
{json.dumps(config, indent=2)}
{err_summary}

## CANVASXPRESS SKILL REFERENCE (Bar Charts)
- graphType: "Bar" – bar charts
- layoutTopology: grid layout (e.g. "3X3" = 3 rows × 3 columns)
- segregateSamplesBy: splits data into panels by a sample annotation field
- colorScheme / colors / colorKey: custom color mapping
- decorations.error: error bars with min/max ranges
- theme: visual styling theme (e.g. "GGPlot")
- barGrouping: "group" = side-by-side bars
- legendPosition / legendColumns: legend layout

Please describe:
1. Chart type and layout (panels, grid structure)
2. What data is shown and how it is organized
3. How data is grouped / samples split into panels
4. What the x-axis and y-axis represent
5. Color coding
6. Error bars and annotations
7. Notable visual styling
8. Scientific interpretation / patterns a scientist would see

CRITICAL: Plain English only. No code. Be specific about panels, grouping,
and data values."""


def build_refined_prompt(
    data: dict,
    config: dict,
    data_info: dict,
    previous_description: str,
    feedback: str,
) -> str:
    """Build a prompt that includes previous description and feedback."""
    base = build_initial_prompt(data, config, data_info)
    base += f"""\

---
## PREVIOUS DESCRIPTION ATTEMPT

{previous_description}

---
## FEEDBACK TO ADDRESS

{feedback}

Please revise your description to address these issues."""
    return base


def _color_key_summary(config: dict) -> str:
    """Summarize color key if present."""
    ck = config.get("colorKey", {})
    colors = config.get("colors", [])
    scheme = config.get("colorScheme", "")
    if not ck and not colors:
        return ""

    lines = []
    if ck:
        parts = [f"{k}={v}" for k, v in ck.items()]
        lines.append(f"- Custom color mapping: {', '.join(parts)}")
    if colors and len(colors) <= 10:
        parts = [f"{v}" for v in colors]
        lines.append(f"- Colors array: {', '.join(parts)}")
    if scheme:
        lines.append(f"- Color scheme: {scheme}")
    return "\n" + "\n".join(lines) if lines else ""


def evaluate_description(
    description: str, config: dict, data_info: dict
) -> tuple[dict, float]:
    """Check whether description covers key chart features. Returns (checks dict, score)."""
    dl = description.lower()

    checks = {
        "mentions_bar_chart": "bar" in dl,
        "mentions_layout": any(x in dl for x in ["panel", "facet", "grid", "layout"]),
        "mentions_grouping": any(
            x in dl for x in ["group", "segregat", "stratify", "categorize"]
        ),
        "mentions_variables": any(v.lower() in dl for v in data_info["vars"]),
        "mentions_error_bars": any(
            x in dl for x in ["error bar", "uncertainty", "variance"]
        ),
        "mentions_xaxis": "x-axis" in dl or "x axis" in dl or "horizontal" in dl,
        "mentions_yaxis": "y-axis" in dl or "y axis" in dl or "vertical" in dl,
        "no_code": "```" not in description and "CanvasXpress" not in description,
    }

    # Check for GGPlot / styling
    if config.get("theme"):
        checks["mentions_theme"] = (
            config["theme"].lower() in dl or "ggplot" in dl or "gridline" in dl
        )

    # Check for custom colors
    if config.get("colorKey"):
        checks["mentions_colors"] = any(
            v.lower() in dl or k.lower() in dl for k, v in config["colorKey"].items()
        )

    passed = sum(1 for v in checks.values() if v)
    score = passed / len(checks) * 100 if checks else 0
    return checks, score


def build_feedback(checks: dict) -> str:
    missing = [f for f, passed in checks.items() if not passed]
    if not missing:
        return ""
    return "Missing from your description:\n" + "\n".join(f"  - {f}" for f in missing)


def generate_prompt(
    filepath: Path,
    example_number: int,
    include_previous: str = "",
    feedback: str = "",
) -> str:
    """Generate a prompt for DeepSeek to describe example N."""
    data, config, _ = extract_example(filepath, example_number)
    data_info = _data_summary(data)

    if include_previous and feedback:
        return build_refined_prompt(data, config, data_info, include_previous, feedback)
    return build_initial_prompt(data, config, data_info)


def refine_description(
    filepath: Path,
    example_number: int,
    iterations: int = 5,
) -> dict:
    """Run the full iterative refinement loop. Returns best description + metadata."""
    data, config, _ = extract_example(filepath, example_number)
    data_info = _data_summary(data)

    best_desc = ""
    best_score = 0
    best_iter = 1

    for i in range(1, iterations + 1):
        feedback = (
            build_feedback(dict(evaluate_description(best_desc, config, data_info)[0]))
            if i > 1
            else ""
        )
        prompt = (
            build_refined_prompt(data, config, data_info, best_desc, feedback)
            if i > 1
            else build_initial_prompt(data, config, data_info)
        )

        resp = call_llm([_build_system_prompt(), {"role": "user", "content": prompt}])
        # Strip any markdown code blocks
        resp = re.sub(r"```.*?\n(.*?)```", r"\1", resp, flags=re.DOTALL).strip()

        checks, score = evaluate_description(resp, config, data_info)

        if score > best_score:
            best_desc = resp
            best_score = score
            best_iter = i

        print(f"Iteration {i}: score={score:.0f}% ({best_iter})")

        if score >= 95:
            print("Good enough, stopping early.")
            break

    return {
        "description": best_desc,
        "score": best_score,
        "iterations": best_iter,
    }


def agent_prompt_from_description(description: str, data: dict, config: dict) -> str:
    """Convert a natural-language description back into an agent prompt."""
    vars_list = data["y"]["vars"]
    n_smps = len(data["y"]["smps"])
    color_key = config.get("colorKey", {})
    n_errors = len(config.get("decorations", {}).get("error", []))
    layout = config.get("layoutTopology", "")
    segregate = config.get("segregateSamplesBy", [])
    theme = config.get("theme", "")
    legend_pos = config.get("legendPosition", "")
    legend_cols = config.get("legendColumns", "")
    xtitle = config.get("xAxisTitle", "")

    colors_str = (
        ", ".join(f"{v}={k}" for k, v in color_key.items())
        if color_key
        else "default colors"
    )

    parts = [
        f"Create a vertical grouped bar chart using CanvasXpress that displays data "
        f"across {len(vars_list)} conditions: {', '.join(vars_list)}.",
    ]

    if layout:
        parts.append(f"The chart should use a {layout} panel grid layout")
        if segregate:
            parts[-1] += (
                f" where each panel is segregated by {segregate[0]} from sample annotations"
            )
        parts[-1] += "."

    parts.append(f"The dataset contains {n_smps} samples.")
    if xtitle:
        parts[-1] += f" Measurements are for {xtitle.lower()}."

    if color_key:
        parts.append(f"Use custom colors: {colors_str}.")

    if n_errors > 0:
        samples = list({e.get("sample", "") for e in config["decorations"]["error"]})
        parts.append(
            f"Include error bars with min/max ranges for specific samples "
            f"({', '.join(samples)}) across multiple genes."
        )

    if theme:
        parts.append(f"Apply the {theme} theme for styling.")

    if legend_pos:
        lc = f" with {legend_cols} columns" if legend_cols else ""
        parts.append(f"Position the legend at the {legend_pos} of the chart{lc}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Chart generation task
# ---------------------------------------------------------------------------


def _build_md_content(chart_type: str, examples: list[dict]) -> str:
    """Build MyST markdown content for a chart type notebook."""
    parts = []

    # Frontmatter
    parts.append("""---
jupytext:
  cell_metadata_filter: -all
  formats: md:myst,ipynb
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.5
kernelspec:
  name: canvasxpress-examples
  display_name: Python 3.12 (CanvasXpress Examples)
  language: python
---

---
jupytext:
  formats: md:myst,ipynb
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.5
---

""")

    # Title
    parts.append(f"# {chart_type.title()} Chart Examples\n\n")

    # MyBinder launch link
    notebook_name = f"{chart_type}.ipynb"
    encoded_notebook = urllib.parse.quote(f"examples/{notebook_name}")
    binder_url = f"{BINDER_BASE}?urlpath=lab/tree/{encoded_notebook}"
    parts.append(
        f"**[Launch in MyBinder]({binder_url})** for live interactive exploration\n\n"
    )

    # Single import cell for all examples
    parts.append("```{code-cell} ipython3\n")
    parts.append("from canvasxpress.canvas import CanvasXpress\n")
    parts.append("from canvasxpress.plot import graph\n")
    parts.append("```\n")

    for i, ex in enumerate(examples, 1):
        parts.append(f"\n## Example {i}: {ex['title']}\n")

        # Source link
        parts.append(f"Source: <{ex['url']}>\n")

        # Description
        if ex.get("description"):
            parts.append(f"{ex['description']}\n")

        # Single code cell with data, config, and render (like bar.md examples 4+)
        parts.append("```{code-cell} ipython3\n")

        # Data cell (assign to 'data' variable)
        if ex.get("data"):
            parts.append(f"data = {ex['data']}\n")

        # Config cell
        if ex.get("config"):
            config_str = _dict_to_python_code(ex["config"])
            parts.append(f"config = {config_str}\n")

        # Render cell
        parts.append("\ncx = CanvasXpress(data=data, config=config)\n")
        parts.append("graph(cx)\n")
        parts.append("```\n")

        # Agent prompt cell
        if ex.get("agent_prompt"):
            parts.append("\n**Agent Prompt:** " + ex["agent_prompt"] + "\n")

    return "".join(parts)


@task(
    help={
        "chart_type": "Chart type (e.g. lollipop, bar, scatter2d)",
        "num_examples": "Number of examples to generate (default: 3)",
    }
)
def chart_generate(ctx: context.Context, chart_type: str, num_examples: int = 3):
    """Generate one or more chart examples from CanvasXpress website.

    1. Fetch HTML from canvasxpress.org
    2. Use DeepSeek to extract JS data and config
    3. I convert to Python CanvasXpress format
    4. Use DeepSeek to generate agent prompt
    5. Write .md file to build/, convert to .ipynb in examples/
    """
    build_dir = Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    ex_dir = Path("examples")
    ex_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {num_examples} {chart_type} chart examples...")
    print(f"Markdown output: {build_dir}\n")
    print(f"Notebook output: {ex_dir}\n")

    examples = []
    for i in range(1, num_examples + 1):
        url = f"https://www.canvasxpress.org/examples/{chart_type}-{i}.html"
        print(f"Fetching {url}...")

        try:
            html = _fetch_html(url)
        except Exception as e:
            print(f"  Warning: Could not fetch {url}: {e}")
            break

        # Step 1: Extract data and config
        if chart_type == "lollipop":
            # Lollipop charts have data in HTML with embedded 2D arrays
            html = _fetch_html(url)
            data, config = _extract_data_and_config_from_html(html)
            if not data or not config:
                print(
                    f"  Warning: Could not extract data/config for lollipop example {i}"
                )
                continue
        else:
            # For other chart types, use DeepSeek to extract from HTML
            html = _fetch_html(url)
            data, config = _extract_data_and_config_from_html(html)

        if not data or not config:
            print(f"  Warning: Could not extract data/config for example {i}")
            continue

        # Step 2: Clean config (keep ALL options - CanvasXpress Python supports all JS options)
        clean_config = {
            k: v
            for k, v in config.items()
            if not k.startswith("on") or k in ["on", "events"]
        }

        # Convert data dict to Python source code (not JSON)
        data_str = _dict_to_python_code(data, indent=2)

        example = {
            "title": f"{chart_type.title()} Chart {i}",
            "url": url,
            "data": data_str,
            "config": clean_config,
        }

        # Step 4: Validate the Python code works
        config_str = _dict_to_python_code(clean_config, indent=2)
        python_code = f"data = {data_str}\nconfig = {config_str}\nfrom canvasxpress.canvas import CanvasXpress\nfrom canvasxpress.plot import convert_to_reproducible_json\ncx = CanvasXpress(data=data, config=config)\nresult = convert_to_reproducible_json(cx)\n"

        try:
            namespace = {"__name__": "__main__", "__builtins__": __builtins__}
            exec(python_code, namespace)
        except Exception as e:
            print(f"  Warning: Code validation failed for example {i}: {e}")
            # Continue anyway but flag it
            example["validated"] = False
        else:
            example["validated"] = True
        print("  Generating title and agent prompt...")
        # Use DeepSeek to generate initial prompt from data/config
        prompt = f"""\
You are a scientific data visualization expert. Given the following chart data and configuration, provide:

1. A descriptive title (5-10 words)
2. A short plain-English description (2-3 sentences)
3. An agent prompt (4-6 sentences) in plain English that a scientist could use to request this chart. MUST mention 'CanvasXpress'. Describe: chart type, data structure, axes, colors, legend, key parameters, and any notable patterns. NO Python code.

Respond in EXACT JSON format:
{{"title": "...", "description": "...", "agent_prompt": "..."}}

Data: {json.dumps(data, indent=2, default=str)[:1500]}

Config: {json.dumps(clean_config, indent=2, default=str)[:800]}"""

        try:
            response = call_llm(
                [
                    {
                        "role": "system",
                        "content": "You are a data visualization expert. Respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )

            ai_response = _extract_json_from_response(response)
            if ai_response:
                example["title"] = ai_response.get("title", example["title"])
                example["description"] = ai_response.get("description", "")
                example["agent_prompt"] = ai_response.get("agent_prompt", "")
        except Exception as e:
            print(f"  Warning: Could not generate AI prompt: {e}")
            example["description"] = ""
            example["agent_prompt"] = (
                f"Create a {chart_type} chart using CanvasXpress with the provided data and configuration."
            )

        examples.append(example)
        print(f"  Example {i}: {example['title']}")

    if not examples:
        print("No examples were generated.")
        return

    # Build and write markdown to build/
    md_file = build_dir / f"{chart_type}.md"

    # Check if file exists and read existing examples
    existing_md = None
    if md_file.exists():
        existing_md = md_file.read_text()
        # Extract existing example titles to avoid duplicates
        import re

        existing_titles = set(re.findall(r"## Example \d+: (.+)", existing_md))
        # Filter out examples that already exist
        new_examples = [ex for ex in examples if ex["title"] not in existing_titles]
        if new_examples:
            # Append new examples to existing content
            new_md_content = _build_md_content(chart_type, new_examples)
            # Skip the frontmatter and title from new content
            if "\n---\n" in new_md_content:
                parts = new_md_content.split("\n---\n", 1)
                if len(parts) > 1:
                    new_md_content = parts[1]
            existing_md += new_md_content
            md_file.write_text(existing_md)
        else:
            print("All examples already exist in the file.")
            return
    else:
        # Create new file with full content
        md_content = _build_md_content(chart_type, examples)
        md_file.write_text(md_content)
    print(f"\nCreated {md_file}")

    # Convert to notebook with jupytext, output to examples/
    ipynb_file = ex_dir / f"{chart_type}.ipynb"
    print("Converting to notebook with jupytext...")
    ctx.run(f"uv run jupytext --to notebook {md_file}", hide=True)
    print(f"Created {ipynb_file}")

    # Clean up any stray md files from examples/
    for f in ex_dir.glob("*.md"):
        f.unlink()

    print(f"\nGenerated {len(examples)} examples:")
    for ex in examples:
        print(f"  - {ex['title']}")


# ---------------------------------------------------------------------------
# Binder configuration
# ---------------------------------------------------------------------------

REPO_OWNER = "docinfosci"
REPO_NAME = "canvasxpress-examples-jupyter"
BRANCH = "main"
BINDER_BASE = f"https://mybinder.org/{REPO_OWNER}/{REPO_NAME}/{BRANCH}"
