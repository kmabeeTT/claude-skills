# MLIR Graph Debug - Usage Examples

## Example 1: Basic Failure Analysis

```bash
/mlir-graph-debug test_opt_generation_rm_hack_feb4_xla_debug2.log
```

**What it does:**
1. Extracts all TTNN graphs from the log
2. Finds the FATAL error
3. Maps the error to Graph 17
4. Traces the data flow through the ttnn.sort operation
5. Identifies that %35 is f32 but sort requires bf16/ui16
6. Recommends inserting a typecast

**Expected Output:**

1. **Analysis report** (`opt_125m_ttnn_sort_type_mismatch_analysis.md`):
```markdown
# MLIR Graph Failure Analysis - OPT-125M ttnn.sort Type Mismatch

## Summary
- Graph: 17
- Failing Operation: ttnn.sort at line 116
- Error: Input tensor data type must be BFLOAT16 or UINT16, got DataType::FLOAT32

## Data Flow
%35 comes from ttnn.where(%34, %27, %10)
  - %34: f32 mask (from bf16→f32 typecast)
  - %27: f32 logits/temperature
  - %10: f32 constant (-inf)

Result: f32 tensor → ttnn.sort (expects bf16/ui16)

## Fix
Insert typecast before sort:
  %35_bf16 = ttnn.typecast(%35) bf16
  ttnn.sort(%35_bf16) ...

## Repro Commands (copy-paste ready)
```bash
ttmlir-opt --ttir-to-ttnn-backend-pipeline="system-desc-path=ttrt-artifacts/system_desc.ttsys" -o opt125m_ttnn.mlir ./opt125m_graph_17_ttir.mlir.txt
ttmlir-translate --ttnn-to-flatbuffer -o out.ttnn opt125m_ttnn.mlir
ttrt run out.ttnn |& tee opt125m_ttrt_run.log
```

See `opt_125m_ttnn_sort_repro.sh` for full automated script.
```

2. **Repro script** (`opt_125m_ttnn_sort_repro.sh`):
```bash
#!/bin/bash
# Repro script for OPT-125M ttnn.sort failure (Graph 17)

set -e

MODEL="opt_125m"
GRAPH_NUM=17
DATE=$(date +%Y-%m-%d)
REPRO_DIR="${MODEL}_ttnn_sort_${DATE}"

echo "=== Creating repro directory: ${REPRO_DIR} ==="
mkdir -p "${REPRO_DIR}" && cd "${REPRO_DIR}"

echo "=== Extracting TTIR graph ${GRAPH_NUM} ==="
python /localdev/kmabee/scripts/extract_mlir_graphs.py ../test.log --type ttir
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

echo "All artifacts in: ${REPRO_DIR}/"
```

**Running the repro script:**
```bash
chmod +x opt_125m_ttnn_sort_repro.sh
./opt_125m_ttnn_sort_repro.sh

# All files are in: opt_125m_ttnn_sort_2026-02-05/
cd opt_125m_ttnn_sort_2026-02-05/
grep FATAL opt_125m_graph_17_ttrt_run.log
```

---

## Example 2: Focus on Specific Graph

```bash
/mlir-graph-debug run.log --graph 5
```

Only analyzes Graph 5, useful when you already know which graph is problematic.

---

## Example 3: Extract Graphs Without Analysis

```bash
/mlir-graph-debug debug.log --extract-only
```

Useful for:
- Quick extraction of all graphs
- Manual inspection needed
- Pre-processing before detailed analysis

---

## Example 4: Generate GitHub Issue

```bash
/mlir-graph-debug failure.log --issue
```

Produces a complete GitHub issue template with:
- Bug summary
- Reproduction steps
- Expected vs actual behavior
- Log snippets
- Suggested fix
- Environment details

You can then copy/paste or pipe to `gh issue create`:

```bash
/mlir-graph-debug failure.log --issue --output /tmp/issue.md
gh issue create --body-file /tmp/issue.md --title "ttnn.sort type mismatch in sampling"
```

---

## Common Patterns Detected

### Type Mismatches
The skill recognizes common patterns like:
- Missing typecasts before ops with type restrictions
- f32 → bf16 conversions needed for hardware ops
- Integer type mismatches (si32 vs ui32)

### Top-P Sampling Issues
Automatically identifies the sampling pattern:
```
logits → f32 → softmax → threshold → masking → sort
                                                   ↑ needs bf16
```

### Shape Mismatches
Detects:
- Reshape errors
- Broadcast incompatibilities
- Dimension mismatches in binary ops

### Memory/Layout Issues
Identifies:
- Missing to_layout conversions
- DRAM vs L1 config problems
- Tile vs row_major layout conflicts

---

## Tips

1. **Keep extraction scripts updated**: Ensure `extract_mlir_graphs.py` is in `../scripts/`

2. **Check multiple IR types**: Sometimes issues appear in earlier stages
   ```bash
   python extract_mlir_graphs.py log.txt --type shlo
   python extract_mlir_graphs.py log.txt --type ttir
   ```

3. **Use with grep for quick checks**:
   ```bash
   grep "ttnn.sort" /tmp/graph_*.mlir
   ```

4. **Combine with other tools**:
   - Use `/show-mlir-modules` to list all modules first
   - Use `/find-pcc-failures` for numerical accuracy issues
   - Use `/analyze-failure` for broader failure analysis

---

## Integration with Workflow

Typical debug workflow:
1. Test fails → check test output log
2. `/mlir-graph-debug test.log` → identifies graph & issue
3. Look at extracted graph in `/tmp/graph_N_ttnn.mlir`
4. Verify fix by checking similar patterns
5. `/mlir-graph-debug test.log --issue` → file bug if compiler issue
6. Or fix test/code if application issue

---

## Future Enhancements (TODO)

- [ ] Auto-detect which MLIR pass introduced the issue
- [ ] Compare graphs before/after passes to see transformations
- [ ] Suggest compiler flags to work around issues
- [ ] Pattern matching against known issues database
- [ ] Visual graph rendering with highlighted failure path
- [ ] Automatic fix patches for common issues
