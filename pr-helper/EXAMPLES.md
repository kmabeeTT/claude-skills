# PR Helper - Usage Examples

## Example 1: After Fixing a Compiler Bug

### Context
Just fixed ttnn.sort to support f32 inputs by adding a workaround pass.

### Invocation
```
User: "Can you help me prepare a PR for the ttnn.sort fix?"
```

### What the Skill Does

**Step 1: Analyze changes**
```bash
$ git status
Modified:
  third_party/tt-mlir/.../TTNNWorkaroundsPass.cpp

Untracked:
  third_party/tt-mlir/.../sort_f32_input_workaround.mlir
  third_party/tt-mlir/.../sort_topk_f32_workaround.mlir
```

**Step 2: Extract context from conversation**
- Problem: ttnn.sort rejected f32 inputs
- Root cause: TTNNWorkaroundsPass didn't insert typecast
- Solution: Added f32→bf16 conversion
- Tests: Created 2 new test files

**Step 3: Ask user**
```
Questions for you:
1. What's the GitHub issue number?
   > 4567

2. Target repository?
   > tt-mlir

3. Branch topic (suggested: sort_f32_workaround)?
   > [accept suggestion]
```

**Step 4: Create branch and commit**
```bash
$ git checkout -b kmabee/sort_f32_workaround_issue_4567
$ git add third_party/tt-mlir/src/tt-mlir/lib/Dialect/TTNN/IR/TTNNWorkaroundsPass.cpp
$ git add third_party/tt-mlir/src/tt-mlir/test/ttmlir/Dialect/TTNN/sort/*.mlir
$ git commit -m "TTNN: Add f32 input workaround for sort operation

- Added input type checking in createSortOpOperandsWorkarounds()
- Insert typecast from f32 to bf16 for sort inputs
- Added test coverage for f32→bf16 conversion
- Added regression test from TopK operation

Fixes #4567"
$ git push -u origin kmabee/sort_f32_workaround_issue_4567
```

**Step 5: Generate PR description file**

Creates `PR_sort_f32_workaround_2026-02-05.md`:

```markdown
# PR: [TTNN] Add f32 input workaround for sort operation

**Branch**: kmabee/sort_f32_workaround_issue_4567
**Target Repo**: tt-mlir
**Issue**: https://github.com/tenstorrent/tt-mlir/issues/4567

## PR Description for GitHub

### Ticket
https://github.com/tenstorrent/tt-mlir/issues/4567

### Problem description
The `ttnn.sort` operation in tt-metal only supports BFloat16 or UInt16 input tensors, but TTIR graphs were passing Float32 inputs. This caused runtime failures with the error:

```
TT_FATAL: Input tensor data type must be BFLOAT16 or UINT16, got DataType::FLOAT32
```

This affected operations like top-k sorting and top-p sampling used in LLM text generation. The TTNNWorkaroundsPass was only handling output indices type conversion but not input tensor type conversion.

### What's changed
Added input tensor type checking in `createSortOpOperandsWorkarounds()` to automatically insert f32→bf16 typecast operations when needed.

**Files Modified**:
- `lib/Dialect/TTNN/IR/TTNNWorkaroundsPass.cpp` (+9/-3) - Added f32 input type checking and bf16 conversion workaround
- `test/ttmlir/Dialect/TTNN/sort/sort_f32_input_workaround.mlir` (new) - Unit test for f32→bf16 conversion
- `test/ttmlir/Dialect/TTNN/sort/sort_topk_f32_workaround.mlir` (new) - Regression test from TopK operation

**Key Changes**:
1. Check input element type in `createSortOpOperandsWorkarounds()`
2. Insert `tensorDataTypeWorkaround = ttcore::DataType::BFloat16` when input is f32
3. Apply same conversion to output values tensor (must match input type)
4. Updated function comments to document both workarounds

**Impact**: This enables f32-based operations like top-k sorting and top-p sampling to work correctly. The compiler now automatically inserts the necessary type conversions, eliminating runtime errors.

### Checklist
- [x] New/Existing tests provide coverage for changes

**Tests Added**:
- `test/ttmlir/Dialect/TTNN/sort/sort_f32_input_workaround.mlir` - Verifies typecast insertion for f32 inputs
- `test/ttmlir/Dialect/TTNN/sort/sort_topk_f32_workaround.mlir` - Full TopK operation that previously failed

**Tests Now Passing**:
- TopK operation with f32 inputs
- OPT-125M top-p sampling (text generation)

---

## Summary for Reference

**Before**:
```mlir
%values, %indices = "ttnn.sort"(%input_f32)
// ERROR: f32 not supported
```

**After**:
```mlir
%input_bf16 = "ttnn.typecast"(%input_f32) {dtype = bf16}
%values, %indices = "ttnn.sort"(%input_bf16)
// Works! Typecast inserted automatically
```

## Commands for Opening PR

```bash
# Already done by skill:
# - Created branch: kmabee/sort_f32_workaround_issue_4567
# - Committed changes
# - Pushed to remote

# To open PR using GitHub CLI:
gh pr create --repo tenstorrent/tt-mlir --base main \
  --title "[TTNN] Add f32 input workaround for sort operation" \
  --body-file PR_sort_f32_workaround_2026-02-05.md

# Or open PR manually in browser:
# https://github.com/tenstorrent/tt-mlir/compare/main...kmabee/sort_f32_workaround_issue_4567
```
```

**Step 6: Summary for user**
```
✅ Branch created: kmabee/sort_f32_workaround_issue_4567
✅ Changes committed and pushed
✅ PR description written to: PR_sort_f32_workaround_2026-02-05.md

📋 Next steps:
1. Review PR_sort_f32_workaround_2026-02-05.md
2. Open PR at: https://github.com/tenstorrent/tt-mlir/pulls
3. Or use: gh pr create --repo tenstorrent/tt-mlir --base main \
            --body-file PR_sort_f32_workaround_2026-02-05.md
```

---

## Example 2: After Adding a New Feature

### Context
Added support for a new TTNN operation.

### Invocation
```
User: "Let's prepare a PR for the new convolution optimization"
```

### Generated PR File

```markdown
# PR: [TTNN/Conv] Add tiling optimization for 3x3 convolutions

**Branch**: kmabee/conv_tiling_optimization_issue_5123
**Target Repo**: tt-mlir
**Issue**: https://github.com/tenstorrent/tt-mlir/issues/5123

### Problem description
3x3 convolutions were not utilizing efficient tiling patterns, causing 30% performance degradation compared to theoretical peak...

### What's changed
Implemented specialized tiling strategy for 3x3 kernels that better utilizes the tensor cores...

**Performance Impact**:
- ResNet-50: 25% speedup
- MobileNet: 18% speedup
```

---

## Example 3: Multi-Repo Change

### Invocation
```
User: "This fix needs PRs in both tt-xla and tt-mlir"
```

### Skill Behavior

Asks which repo to handle first, then:

1. Creates PR for tt-mlir:
   - Branch: `kmabee/fix_topic_issue_123`
   - File: `PR_tt-mlir_fix_topic_2026-02-05.md`

2. Creates PR for tt-xla:
   - Branch: `kmabee/fix_topic_issue_124`
   - File: `PR_tt-xla_fix_topic_2026-02-05.md`
   - References tt-mlir PR in description

3. Provides commands for both PRs

---

## Tips

### Good PR Titles (< 70 chars)
✅ `[TTNN] Add f32 input workaround for sort operation`
✅ `[Workarounds] Support f32→bf16 typecast in sort`
✅ `Fix type mismatch in sort operation for f32 inputs`

❌ `Fixed the issue where ttnn.sort was failing when given float32 inputs by adding a workaround`

### Comprehensive Problem Descriptions
Include:
- What was failing (specific error)
- Why it was failing (root cause)
- Where it was failing (file/function)
- What operations were affected

### Clear Impact Statements
- "Enables top-k and sampling operations"
- "Fixes text generation for OPT-125M model"
- "Reduces compilation time by 15%"
- "Improves numerical accuracy for mixed precision"
