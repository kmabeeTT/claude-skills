---
name: pr-helper
description: This skill should be used when the user asks to "prepare PR", "open pull request", "create PR description", "help with PR", or after completing a fix/feature and wants to submit it for review.
version: 1.0.0
---

# PR Helper Skill

You are a specialist in preparing pull request descriptions for code changes in TT-XLA and tt-mlir projects.

## Your Task

After a debug session or feature implementation, help the user prepare a pull request by:
1. Analyzing the changes made
2. Gathering context from the conversation
3. Filling in the PR template
4. Creating a branch and committing changes
5. Generating a PR description file for easy submission

## Workflow

### Step 1: Analyze Recent Changes

Check what files were modified:
```bash
git status
git diff --stat
git log --oneline -5
```

Identify:
- Files changed
- Tests added
- Documentation updates
- Configuration changes

### Step 2: Gather Context from Session

From the conversation, extract:
- **Problem description**: What was the issue? What was failing?
- **Root cause**: Why did it happen?
- **Solution approach**: How was it fixed?
- **Impact**: What does this fix enable?
- **Tests**: What tests were added or now pass?

### Step 3: Ask User for Issue Information

Use AskUserQuestion to get:
- GitHub issue number
- Whether this should go to tt-xla or tt-mlir (or both)
- Branch topic name (suggest based on fix)

### Step 4: Generate PR Description

Create a file: `PR_<topic>_<date>.md`

**Template**:
```markdown
# PR: <Concise title>

**Branch**: `kmabee/<topic>_issue_<XXX>`
**Target Repo**: tt-xla | tt-mlir
**Issue**: [Link to be filled]

## PR Description for GitHub

### Ticket
Link to Github Issue

### Problem description
<From conversation: What was failing? What was the error? Why did it happen?>

### What's changed
<Describe the fix approach, files modified, and impact>

**Files Modified**:
- `path/to/file.cpp` - <brief description>
- `path/to/test.mlir` - <brief description>

**Key Changes**:
1. <Change 1>
2. <Change 2>

**Impact**: <What this enables/fixes>

### Checklist
- [x] New/Existing tests provide coverage for changes

**Tests Added**:
- `test/path/to/test.mlir` - <what it tests>

**Tests Now Passing**:
- <List tests that were failing but now pass>

---

## Summary for Reference

**Before**: <What was broken>
**After**: <What works now>

## Commands for Opening PR

```bash
# Already done by skill:
# - Created branch: kmabee/<topic>_issue_<XXX>
# - Committed changes
# - Pushed to remote

# To open PR using GitHub CLI:
gh pr create --repo tenstorrent/<repo> --base main \
  --title "<Concise PR title>" \
  --body-file PR_<topic>_<date>.md

# Or open PR manually in browser:
# https://github.com/tenstorrent/<repo>/compare/main...kmabee/<topic>_issue_<XXX>
```
```

### Step 5: Create Branch and Commit

```bash
# Create and checkout branch
git checkout -b kmabee/<topic>_issue_<XXX>

# Stage changes
git add <files>

# Commit with descriptive message
git commit -m "<Component>: <Brief description>

<Detailed description>

Fixes #<issue_number>"

# Push to remote
git push -u origin kmabee/<topic>_issue_<XXX>
```

### Step 6: Output Summary

Tell the user:
1. ✅ Branch created and pushed
2. ✅ PR description written to file
3. ✅ Ready to open PR
4. 📄 Show the PR description file path
5. 🔗 Provide gh CLI command to open PR

## Key Principles

1. **Be comprehensive**: Include all relevant context from the debug session
2. **Be specific**: Reference exact files, line numbers, functions
3. **Show impact**: Explain what this enables or fixes
4. **Include tests**: Always mention test coverage
5. **Be concise in title**: PR title should be < 70 chars
6. **Use conventional commits**: Format: `<component>: <brief description>`

## Example Usage

**User**: "Can you help me prepare a PR for the ttnn.sort fix?"

**Agent**:
1. Check git status to see changes
2. Analyze conversation for context
3. Ask for issue number and repo
4. Generate PR description with:
   - Problem: ttnn.sort didn't support f32 inputs
   - Fix: Added typecast workaround in TTNNWorkaroundsPass
   - Tests: Added sort_f32_input_workaround.mlir
   - Impact: Enables top-k and sampling operations
5. Create branch: `kmabee/sort_f32_workaround_issue_4567`
6. Commit and push changes
7. Write `PR_sort_f32_workaround_2026-02-05.md`
8. Provide next steps

## Additional Features

### Smart PR Title Generation

Generate concise titles:
- Format: `[Component] Brief description`
- Examples:
  - `[TTNN] Add f32 input workaround for sort operation`
  - `[Workarounds] Support f32→bf16 typecast in sort`
  - `[TTNN/Sort] Fix type mismatch for f32 inputs`

### Files Changed Summary

Provide a structured summary:
```
Modified:
  - lib/Dialect/TTNN/IR/TTNNWorkaroundsPass.cpp (+15/-3)
    Added f32 input type checking and bf16 conversion

Added:
  - test/ttmlir/Dialect/TTNN/sort/sort_f32_input_workaround.mlir
    Test for f32→bf16 workaround
  - test/ttmlir/Dialect/TTNN/sort/sort_topk_f32_workaround.mlir
    Regression test from TopK operation
```

### Before/After Snippets

Include code snippets when relevant:
```cpp
// Before
TTNNOperandWorkarounds operandWorkaround;
return ... .addInputOperandWorkaround(operandWorkaround)

// After
TTNNOperandWorkarounds inputWorkaround;
if (inputElementType.isF32()) {
  inputWorkaround.tensorDataTypeWorkaround = ttcore::DataType::BFloat16;
}
return ... .addInputOperandWorkaround(inputWorkaround)
```

## Output Files

Generate in current directory:
- `PR_<topic>_YYYY-MM-DD.md` - Full PR description
- Optional: `COMMITS.md` - List of commits in this PR

## Tips

- **Reference issue**: Always link to the GitHub issue
- **Credit collaborators**: Mention if someone helped debug
- **Link related PRs**: If there are related changes in other repos
- **Add screenshots**: For UI changes or test output
- **Performance impact**: Mention if there are perf implications
