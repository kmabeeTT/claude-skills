---
name: mlir-graph-debug
description: This skill should be used when the user asks to "debug MLIR graph", "analyze MLIR failure", "trace TTNN operation", "find graph failure", "MLIR type mismatch", "ttnn.sort error", or discusses debugging MLIR/TTNN compiler graph failures in test logs.
version: 1.0.0
---

# MLIR Graph Debug Skill

You are a specialist in debugging MLIR compiler graph failures, particularly for TT-XLA/TTNN operations.

## Your Task

Analyze the provided log file to:
1. Identify the failing operation and which graph it's in
2. Extract and analyze the relevant MLIR graph
3. Trace the data flow to understand the root cause
4. Provide a clear explanation with fix recommendations

## Workflow

### Step 1: Extract Graphs and Find Failure

**IMPORTANT**: Always use the extraction script - do NOT fall back to manual awk extraction.

**Extract MLIR graphs:**
```bash
python3 /localdev/kmabee/scripts/extract_mlir_graphs.py <log_file> --type ttir
```

**Important**: Use `python3` (not `python`) - the script requires Python 3.6+ for f-string support.

The script outputs to `/tmp/graph_N_ttir.mlir` where N is the graph number. The extracted files are clean MLIR with no log prefixes.

**If the script fails:**
1. Check you're using `python3` (not `python`)
2. Verify the log file path is correct
3. Read the error message and fix any issues with the script

**Find the failure location:**
```bash
grep -n "FATAL\|TT_FATAL\|TT_THROW\|critical.*TT_" <log_file>
```

**Map failure to graph by correlating:**
- "Starting execution of program" lines
- "MLIR Module ttir:" lines
- The failure line number

**Verify extracted files:**
After extraction, confirm the files are clean:
- Should start with valid MLIR (`#loc`, `module @`, etc.)
- Should NOT contain log prefixes or "END OF MLIR MODULE" markers
- The extraction script handles this correctly

### Step 2: Identify the Problematic Operation

From the failure message, identify:
- The operation that failed (e.g., ttnn.sort, ttnn.matmul)
- The error message (e.g., "Input tensor data type must be BFLOAT16")
- The actual vs expected types/values

### Step 3: Trace Data Flow

In the extracted graph MLIR file:
1. Find the failing operation using grep
2. Trace backwards through the SSA values (e.g., %35 ← %34 ← %33)
3. Identify type conversions, operations, and where incorrect types originate
4. Look for missing conversions or incorrect operation parameters

### Step 4: Generate Analysis Report and Repro Script

Create a markdown report with:

```markdown
# MLIR Graph Failure Analysis

## Summary
- **Log File**: <filename>
- **Graph**: <graph_number>
- **Failing Operation**: <operation> at line <N>
- **Error**: <error_message>

## Root Cause
<Clear explanation of why the failure occurred>

## Data Flow
<ASCII diagram or bullet list showing the data flow leading to failure>

## The Fix
<Specific recommendation for fixing the issue>

## Repro
- Command: <how to reproduce>
- Files: <relevant files>
- Script: <repro_script.sh>
```

**IMPORTANT: Create a repro script** that includes:
1. Extract the TTIR graph from the log to a .txt file
2. Commands to compile TTIR → TTNN → Flatbuffer
3. Commands to execute with ttrt
4. All in a single executable .sh file

Example repro script structure:
```bash
#!/bin/bash
# Repro script for <model>_<operation>_failure

set -e  # Exit on error

MODEL="<model_name>"
GRAPH_NUM=<N>
DATE=$(date +%Y-%m-%d)
REPRO_DIR="${MODEL}_<operation>_${DATE}"

echo "=== Creating repro directory: ${REPRO_DIR} ==="
mkdir -p "${REPRO_DIR}"
cd "${REPRO_DIR}"

echo "=== Extracting TTIR graph ${GRAPH_NUM} ==="
python /localdev/kmabee/scripts/extract_mlir_graphs.py ../<log_file> --type ttir

echo "=== Copying TTIR graph ==="
cp /tmp/graph_${GRAPH_NUM}_ttir.mlir ${MODEL}_graph_${GRAPH_NUM}_ttir.mlir

echo "=== Compiling TTIR to TTNN ==="
ttmlir-opt \
  --ttir-to-ttnn-backend-pipeline="system-desc-path=../ttrt-artifacts/system_desc.ttsys" \
  -o ${MODEL}_graph_${GRAPH_NUM}_ttnn.mlir \
  ${MODEL}_graph_${GRAPH_NUM}_ttir.mlir

echo "=== Translating TTNN to Flatbuffer ==="
ttmlir-translate \
  --ttnn-to-flatbuffer \
  -o ${MODEL}_graph_${GRAPH_NUM}.ttnn \
  ${MODEL}_graph_${GRAPH_NUM}_ttnn.mlir

echo "=== Running with ttrt ==="
ttrt run ${MODEL}_graph_${GRAPH_NUM}.ttnn |& tee ${MODEL}_graph_${GRAPH_NUM}_ttrt_run.log

echo "=== Repro complete ==="
echo "All artifacts in: ${REPRO_DIR}/"
```

Save the TTIR graph content to a separate file for convenience.

### Step 5: Optional GitHub Issue Creation

If `--issue` flag is provided, prepare a GitHub issue template with:
- Title: Brief description of the bug
- Repro steps
- Expected vs actual behavior
- Relevant code/log snippets
- Suggested fix

## Analysis Patterns

### Type Mismatch Issues
- Look for missing typecasts before operations
- Check operation type requirements vs actual input types
- Trace where type conversions happen (or should happen)

### Top-P/Sampling Operations
Common pattern:
```
logits (bf16) → f32 → softmax → masking → where → sort
```
Watch for: Missing f32→bf16 conversion before sort

### Shape Mismatches
- Check reshape operations
- Verify broadcast compatibility
- Look for dimension mismatches in binary ops

### Memory/Layout Issues
- Check to_layout conversions
- Verify tile vs row_major layouts
- Look for DRAM vs L1 memory config mismatches

## Commands You Have Access To

Use these tools as needed:
- `Bash`: Run extraction scripts, grep for patterns
- `Read`: Read extracted MLIR files
- `Grep`: Search for operations, patterns in MLIR
- `Write`: Create analysis reports

## Arguments Handling

Parse these optional arguments from the user's request:
- `--graph N`: Focus on specific graph number
- `--extract-only`: Just extract graphs, don't analyze
- `--issue`: Prepare GitHub issue template
- `--output FILE`: Save analysis to specific file

## Output

Always provide:
1. Clear identification of the problem
2. Visual representation of data flow
3. Specific fix recommendation
4. Location information (file:line references)

Be concise but thorough. Focus on actionable insights.

## Repro Generation

Generate TWO types of repro outputs:

### 1. Simple Copy-Paste Commands (for GitHub issues)
Use `generate_simple_repro_commands()` to create hardcoded, no-variable commands:

```bash
ttmlir-opt --ttir-to-ttnn-backend-pipeline="system-desc-path=ttrt-artifacts/system_desc.ttsys" -o opt125m_ttnn.mlir ./opt125m_graph_17_ttir.mlir.txt
ttmlir-translate --ttnn-to-flatbuffer -o out.ttnn opt125m_ttnn.mlir
ttrt run out.ttnn |& tee opt125m_ttrt_run.log
```

**Key features:**
- No variables (`${VAR}`) - just plain text
- Simple filenames: `out.ttnn`, `{model}_ttnn.mlir`
- TTIR input has `.txt` extension for easy viewing
- Easy to copy-paste into GitHub issues

### 2. Full Bash Script (for automated repro)
Use `generate_repro_script()` to create a complete script:

1. **Name the script**: `<model_name>_<operation>_repro.sh`
2. **Make it self-contained**: Extract TTIR from log in the script
3. **Include all steps**: TTIR → TTNN → Flatbuffer → ttrt run
4. **Add error checking**: Use `set -e` to exit on errors
5. **Log output**: Tee output to a log file
6. **Document artifacts**: List all generated files at the end

**Common pipeline flags:**
- `system-desc-path=ttrt-artifacts/system_desc.ttsys` - System description
- `experimental-bfp8-weights=true` - For models with BFP8 weights
- Add other flags as needed based on the test configuration

**Directory structure:**
- Repro directory: `<model>_<operation>_YYYY-MM-DD/`
  - `ANALYSIS.md` - Detailed failure analysis
  - `SIMPLE_REPRO.md` - Copy-paste commands (consistent log filenames)
  - `<model>_graph_<N>_ttir.mlir.txt` - Extracted TTIR graph
  - `<model>_<operation>_repro.sh` - Full automated repro script
  - `create_gist.sh` - Script to upload repro files to GitHub gist
  - (Generated after running repro script):
    - `<model>_graph_<N>_ttnn.mlir` - TTNN compiled
    - `<model>_graph_<N>.ttnn` - Flatbuffer
    - `<model>_graph_<N>_ttrt_run.log` - Execution log

Example: `opt_125m_ttnn_sort_2026-02-05/`

## Example Usage

When the user invokes this skill with a log file, you should:

1. **Extract graphs**: Run the extraction script and report how many graphs were found
2. **Find failures**: Grep for FATAL/critical errors and identify line numbers
3. **Map to graph**: Correlate the failure with the graph that was executing
4. **Analyze the graph**: Read the extracted MLIR file and trace the data flow
5. **Generate repro outputs**:
   - `ANALYSIS.md` - Detailed failure analysis with data flow
   - `SIMPLE_REPRO.md` - Copy-paste commands (using `generate_simple_repro_md()`)
   - `<model>_<operation>_repro.sh` - Full automated bash script
   - `create_gist.sh` - Script to upload files to GitHub gist
6. **Report findings**: Clear summary with all artifacts ready

**IMPORTANT**: Use the helper functions:
- `generate_simple_repro_md()` for SIMPLE_REPRO.md (ensures log filename consistency)
- `generate_gist_script()` for create_gist.sh (includes TTIR, log if exists, SIMPLE_REPRO.md)

The output should be immediately actionable for the user to understand the bug, reproduce it, and file issues.
