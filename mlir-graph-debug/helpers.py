#!/usr/bin/env python3
"""
Helper utilities for MLIR graph debugging.
"""

import re
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class MLIRModule:
    """Represents an MLIR module found in logs."""
    graph_num: int
    ir_type: str  # 'ttnn', 'ttir', 'shlo', etc.
    line_num: int
    module_name: Optional[str] = None


@dataclass
class ProgramExecution:
    """Represents a program execution found in logs."""
    execution_num: int
    line_num: int
    first_op: Optional[str] = None


@dataclass
class Failure:
    """Represents a failure/error found in logs."""
    line_num: int
    error_type: str  # 'FATAL', 'THROW', 'ERROR'
    message: str
    operation: Optional[str] = None


def parse_mlir_modules(log_lines: List[str], ir_type: str = 'ttnn') -> List[MLIRModule]:
    """Parse MLIR module locations from log lines."""
    modules = []
    pattern = rf'MLIR Module {ir_type}:'

    for i, line in enumerate(log_lines, 1):
        if re.search(pattern, line):
            modules.append(MLIRModule(
                graph_num=len(modules) + 1,
                ir_type=ir_type,
                line_num=i
            ))

    return modules


def parse_program_executions(log_lines: List[str]) -> List[ProgramExecution]:
    """Parse program execution starts from log lines."""
    executions = []
    pattern = r'Starting execution of program: main'

    for i, line in enumerate(log_lines, 1):
        if re.search(pattern, line):
            # Try to get the first operation
            first_op = None
            if i < len(log_lines):
                next_line = log_lines[i]
                op_match = re.search(r'Executing operation: (.+)', next_line)
                if op_match:
                    first_op = op_match.group(1)[:80]

            executions.append(ProgramExecution(
                execution_num=len(executions) + 1,
                line_num=i,
                first_op=first_op
            ))

    return executions


def parse_failures(log_lines: List[str]) -> List[Failure]:
    """Parse failures/errors from log lines."""
    failures = []

    for i, line in enumerate(log_lines, 1):
        # Check for FATAL errors
        if 'TT_FATAL' in line or 'critical' in line:
            msg_match = re.search(r'TT_FATAL: (.+)', line)
            if msg_match:
                message = msg_match.group(1)
            else:
                message = line.strip()

            # Try to find the operation from previous lines
            operation = None
            if i > 0:
                prev_line = log_lines[i-2]
                op_match = re.search(r'Executing operation: (.+)', prev_line)
                if op_match:
                    operation = op_match.group(1)

            failures.append(Failure(
                line_num=i,
                error_type='FATAL',
                message=message,
                operation=operation
            ))

    return failures


def map_failure_to_graph(
    failure: Failure,
    modules: List[MLIRModule],
    executions: List[ProgramExecution]
) -> Optional[int]:
    """Map a failure to its corresponding MLIR graph number."""

    # Find the execution that contains this failure
    failure_execution = None
    for i, exec in enumerate(executions):
        # Check if failure is between this execution and the next
        next_line = executions[i+1].line_num if i+1 < len(executions) else float('inf')
        if exec.line_num < failure.line_num < next_line:
            failure_execution = exec
            break

    if not failure_execution:
        return None

    # Find the MLIR module that corresponds to this execution
    for i, module in enumerate(modules):
        # Find the first execution after this module
        next_exec = None
        for exec in executions:
            if exec.line_num > module.line_num:
                next_exec = exec
                break

        if next_exec and next_exec.line_num == failure_execution.line_num:
            return module.graph_num

    return None


def generate_repro_script(
    model_name: str,
    graph_num: int,
    log_file: str,
    operation: str,
    additional_flags: str = ""
) -> str:
    """Generate a bash repro script for the failure."""

    script = f"""#!/bin/bash
# Repro script for {model_name} {operation} failure (Graph {graph_num})
# Generated from: {log_file}

set -e  # Exit on error

MODEL="{model_name}"
GRAPH_NUM={graph_num}
DATE=$(date +%Y-%m-%d)
REPRO_DIR="${{MODEL}}_{operation}_${{DATE}}"

echo "=== Creating repro directory: ${{REPRO_DIR}} ==="
mkdir -p "${{REPRO_DIR}}"
cd "${{REPRO_DIR}}"

echo "=== Extracting TTIR graph ${{GRAPH_NUM}} from {log_file} ==="
python /localdev/kmabee/scripts/extract_mlir_graphs.py ../{log_file} --type ttir

echo "=== Copying TTIR graph to repro directory ==="
cp /tmp/graph_${{GRAPH_NUM}}_ttir.mlir ${{MODEL}}_graph_${{GRAPH_NUM}}_ttir.mlir

echo "=== Compiling TTIR to TTNN ==="
ttmlir-opt \\
  --ttir-to-ttnn-backend-pipeline="system-desc-path=../ttrt-artifacts/system_desc.ttsys{additional_flags}" \\
  -o ${{MODEL}}_graph_${{GRAPH_NUM}}_ttnn.mlir \\
  ${{MODEL}}_graph_${{GRAPH_NUM}}_ttir.mlir

echo "=== Translating TTNN to Flatbuffer ==="
ttmlir-translate \\
  --ttnn-to-flatbuffer \\
  -o ${{MODEL}}_graph_${{GRAPH_NUM}}.ttnn \\
  ${{MODEL}}_graph_${{GRAPH_NUM}}_ttnn.mlir

echo "=== Running with ttrt ==="
ttrt run ${{MODEL}}_graph_${{GRAPH_NUM}}.ttnn |& tee ${{MODEL}}_graph_${{GRAPH_NUM}}_ttrt_run.log

echo ""
echo "=== Repro complete ==="
echo "All artifacts in: ${{REPRO_DIR}}/"
echo "Generated files:"
echo "  - ${{MODEL}}_graph_${{GRAPH_NUM}}_ttir.mlir (TTIR input)"
echo "  - ${{MODEL}}_graph_${{GRAPH_NUM}}_ttnn.mlir (TTNN compiled)"
echo "  - ${{MODEL}}_graph_${{GRAPH_NUM}}.ttnn (Flatbuffer)"
echo "  - ${{MODEL}}_graph_${{GRAPH_NUM}}_ttrt_run.log (Execution log)"
echo ""
echo "Check the log for the failure: grep FATAL ${{MODEL}}_graph_${{GRAPH_NUM}}_ttrt_run.log"
"""
    return script


def generate_simple_repro_commands(
    model_name: str,
    graph_num: int,
    additional_flags: str = ""
) -> str:
    """
    Generate simple, hardcoded repro commands for copy-paste into GitHub issues.
    No variables, just plain commands.
    """

    # Create simple file names
    ttir_input = f"./{model_name}_graph_{graph_num}_ttir.mlir.txt"
    ttnn_output = f"{model_name}_ttnn.mlir"
    flatbuffer_output = "out.ttnn"
    log_output = f"{model_name}_ttrt_run.log"

    # Build pipeline flags
    pipeline_flags = f"system-desc-path=ttrt-artifacts/system_desc.ttsys"
    if additional_flags:
        pipeline_flags = f"{additional_flags} {pipeline_flags}"

    commands = f"""ttmlir-opt --ttir-to-ttnn-backend-pipeline="{pipeline_flags}" -o {ttnn_output} {ttir_input}
ttmlir-translate --ttnn-to-flatbuffer -o {flatbuffer_output} {ttnn_output}
ttrt run {flatbuffer_output} |& tee {log_output}"""

    return commands


def generate_github_issue(
    title: str,
    summary: dict,
    data_flow: str,
    fix_recommendation: str,
    repro_command: str = "",
    repro_script: str = "",
    log_snippet: str = ""
) -> str:
    """Generate a GitHub issue markdown template."""

    issue = f"""## Bug Report: {title}

### Summary
- **Graph**: {summary.get('graph', 'N/A')}
- **Failing Operation**: {summary.get('operation', 'N/A')}
- **Error**: {summary.get('error', 'N/A')}

### Root Cause
{summary.get('root_cause', 'See analysis below')}

### Data Flow
```
{data_flow}
```

### Expected Behavior
The operation should accept the input tensor type, or the compiler should insert appropriate type conversions.

### Actual Behavior
The operation fails at runtime with a type mismatch error.

### Reproduction
"""

    if repro_command:
        issue += f"```bash\n{repro_command}\n```\n\n"

    if repro_script:
        issue += f"### Repro Script\n\nSee attached `{repro_script}` for automated reproduction.\n\n"

    issue += "### Logs\n"
    if log_snippet:
        issue += f"```\n{log_snippet}\n```\n\n"

    issue += f"""### Suggested Fix
{fix_recommendation}

### Environment
- TT-XLA version: [from log/git]
- Hardware: [Grayskull/Wormhole/etc]
- Test: [test name if applicable]
"""

    return issue


if __name__ == '__main__':
    print("MLIR Graph Debug Helpers")
    print("Import this module to use helper functions")
