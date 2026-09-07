---
name: notebook-from-example
description: Create Jupyter notebooks from CanvasXpress online chart examples. Uses DeepSeek as a user-proxy to refine agent prompts that scientists/students could use to request equivalent CanvasXpress charts. Workflow: inspect example → create markdown notebook → test prompt with DeepSeek → refine prompt → regenerate notebook.
---

## Workflow

### 1. Inspect the CanvasXpress Example
Fetch the HTML page for the chart example (e.g., `https://www.canvasxpress.org/examples/bar-1.html`). Extract:
- Chart title (use lowercase, descriptive)
- URL to original example
- Description text
- Data values (from the JavaScript data array or HTML/JS code block)
- Configuration parameters (graphType, orientation, labels, dimensions, legend settings)

### 2. Create the Notebook Markdown
Write a MyST markdown file (`.md`) with cells for:
1. **Title cell**: Markdown heading with chart name (lowercase)
2. **Source cell**: Link to original example ("The original JS example: URL")
3. **Description cell**: Chart description text
4. **Import cell**: `from canvasxpress.canvas import CanvasXpress` and `from canvasxpress.plot import graph`
5. **Data cell**: Pandas DataFrame with black-formatted code (trailing commas, proper indentation)
6. **Config cell**: CanvasXpress object with config dict (black-formatted)
7. **Render cell**: `graph(cx)`
8. **Agent prompt cell**: Refined prompt in a text code block

### 3. Generate the Agent Prompt with DeepSeek
The agent prompt should be in **plain English** that a scientist/student could use. It must NOT contain Python syntax or API details.

**Use DeepSeek as a user-proxy:**

```bash
# Step 1: Prompt the user for their API token (do not hardcode it)
# Then use the token in session memory only:
read -s API_TOKEN
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{
    "model": "DeepSeek-R1-Distill-Qwen-7B-4bit",
    "messages": [
      {"role": "user", "content": "You are an AI agent with CanvasXpress knowledge. Here is the skill:\n\n<skill content>\n\nGiven this user prompt, generate the Python code. Output ONLY code in a code block.\n\n<prompt>"}
    ],
    "temperature": 0.7,
    "max_tokens": 2000
  }'
```

# Step 2: Show DeepSeek the differences between generated code and notebook code
# Ask it to refine the prompt (plain English, no API details)

# Step 3: Repeat until the prompt produces code close to the notebook

### 4. Prompt Refinement Rules
- **DO**: Use plain English, describe chart appearance, reference data variables
- **DO NOT**: Use Python syntax, API parameter names, or code examples
- **MUST**: Explicitly mention "CanvasXpress" to avoid Plotly/matplotlib output
- **MUST**: Describe data in user-friendly terms (categories, values, columns)
- **MUST**: Describe chart appearance (type, orientation, labels, legend, dimensions)

### 5. Key Lessons Learned
1. DeepSeek will hallucinate wrong CanvasXpress API unless given the skill md
2. Prompts must be in plain English - the end user knows nothing about Python/CanvasXpress
3. The coder (Qwen) knows CanvasXpress well - the prompt just needs to describe what they want
4. Axis labels can be confusing - in CanvasXpress vertical bar charts, samples (categories) appear on x-axis but the config uses different parameter names
5. Iterative refinement: generate → compare → refine → repeat (usually 3-4 iterations)
6. Black formatting: trailing commas, proper indentation, wrapped lines for long lists

### 6. Convert Markdown to Notebook
```bash
uv run jupytext --from myst --to notebook examples/bar.md
```

### 7. Verify
Check the notebook has correct cells:
- Markdown cells for title, source, description, agent prompt
- Code cells for imports, data, config, render
- Kernel metadata references the project's Python environment

## Example Prompt Structure
```
Create a vertical bar chart using CanvasXpress. The x-axis should have 5 categories named Cat 1 through Cat 5. The y-axis will display the values for Var 1, which are 4, 5, 4, 4, and 7. Each bar's height corresponds to these values. The y-axis must be labeled 'Var 1'. The chart's title should be 'Bar graph with a single series'. The chart should be 600x600 pixels in size. There should be no legend. The category labels on the x-axis should be rotated 90 degrees for better readability. The data is provided in a pandas DataFrame where the categories are the index and Var 1 is the column.
```

<small>Note that canvasxpress-python must be installed for this skill to work as it provides the necessary agent skills.</small>
