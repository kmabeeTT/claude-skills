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
6. **Optionally prepares GitHub issue** with all relevant details

## Output Format

The skill produces a structured analysis report containing:
- Summary of the failure (graph, operation, error)
- Complete data flow trace
- Root cause explanation
- Specific fix recommendations
- File and line references

## Prerequisites

- Log file with MLIR module dumps
- `extract_mlir_graphs.py` script available in `../scripts/`
- Execution logs with "Starting execution" and error messages

## Future Enhancements

- Automatic GitHub issue creation via `gh` CLI
- Integration with MLIR visualization tools
- Pattern library for common failure modes
- Automated fix suggestions with code patches
