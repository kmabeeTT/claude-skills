# MLIR Graph Debug Skill

Debug MLIR/TTNN graph failures by analyzing execution logs, extracting graphs, and tracing data flow to identify root causes.

## Usage

```bash
/mlir-graph-debug <log_file> [options]
```

## Options

- `--graph N` - Focus analysis on specific graph number
- `--extract-only` - Only extract graphs without full analysis
- `--issue` - Generate GitHub issue template with findings
- `--output FILE` - Save analysis to specific file (default: stdout)

## Examples

### Basic Analysis
```bash
/mlir-graph-debug test_opt_generation.log
```

### Focus on Specific Graph
```bash
/mlir-graph-debug run.log --graph 17
```

### Extract Graphs Only
```bash
/mlir-graph-debug debug.log --extract-only
```

### Prepare GitHub Issue
```bash
/mlir-graph-debug failure.log --issue
```

## What It Does

1. **Extracts MLIR graphs** from the log file using the extraction script
2. **Identifies the failure** by finding FATAL/critical errors
3. **Maps the failure to a graph** by correlating execution lines
4. **Traces data flow** through SSA values to find the root cause
5. **Generates a report** with clear explanation and fix recommendations
6. **Creates a repro script** with TTIR extraction and compilation commands
7. **Optionally prepares GitHub issue** with all relevant details

## Output Format

The skill produces:

### 1. Analysis Report (Markdown)
- Summary of the failure (graph, operation, error)
- Complete data flow trace
- Root cause explanation
- Specific fix recommendations
- File and line references

### 2. Simple Repro Commands
Copy-paste ready commands for GitHub issues (no variables):
```bash
ttmlir-opt --ttir-to-ttnn-backend-pipeline="system-desc-path=ttrt-artifacts/system_desc.ttsys" -o opt125m_ttnn.mlir ./opt125m_graph_17_ttir.mlir.txt
ttmlir-translate --ttnn-to-flatbuffer -o out.ttnn opt125m_ttnn.mlir
ttrt run out.ttnn |& tee opt125m_ttrt_run.log
```

### 3. Full Repro Script (Bash)
A self-contained script that:
- Creates a dated subdirectory for all artifacts
- Extracts the TTIR graph from the log
- Compiles TTIR → TTNN using `ttmlir-opt`
- Translates TTNN → Flatbuffer using `ttmlir-translate`
- Executes with `ttrt run`
- Captures output to a log file

Example: `opt_125m_ttnn_sort_repro.sh`

```bash
#!/bin/bash
# Creates opt_125m_ttnn_sort_2026-02-05/ directory
# Extracts graph, compiles, and runs to reproduce the failure

DATE=$(date +%Y-%m-%d)
REPRO_DIR="opt_125m_ttnn_sort_${DATE}"
mkdir -p "${REPRO_DIR}" && cd "${REPRO_DIR}"

python /localdev/kmabee/scripts/extract_mlir_graphs.py ../test.log --type ttir
ttmlir-opt --ttir-to-ttnn-backend-pipeline="..." -o model_ttnn.mlir model_ttir.mlir
ttmlir-translate --ttnn-to-flatbuffer -o model.ttnn model_ttnn.mlir
ttrt run model.ttnn |& tee model_ttrt_run.log
```

**Directory structure:**
```
opt_125m_ttnn_sort_2026-02-05/
├── opt_125m_graph_17_ttir.mlir
├── opt_125m_graph_17_ttnn.mlir
├── opt_125m_graph_17.ttnn
└── opt_125m_graph_17_ttrt_run.log
```

## Prerequisites

- Log file with MLIR module dumps
- `extract_mlir_graphs.py` script available in `../scripts/`
- Execution logs with "Starting execution" and error messages

## Future Enhancements

- Automatic GitHub issue creation via `gh` CLI
- Integration with MLIR visualization tools
- Pattern library for common failure modes
- Automated fix suggestions with code patches
