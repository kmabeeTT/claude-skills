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

### Step 4: Generate PR Files

**IMPORTANT**: Generate TWO separate files:

1. **`PR_DESCRIPTION.md`** - Clean, concise PR body (becomes merge commit message)
2. **`PR_DETAILS.md`** - Detailed context for posting as a comment

#### File 1: PR_DESCRIPTION.md

**Purpose**: Clean PR description that becomes the merge commit message. Keep it brief!

**Template** (following tt-mlir convention):
```markdown
### Ticket
<Link to Github Issue>

### Problem description
<What was failing? What was the error? Keep it concise - 2-3 paragraphs max>

### What's changed
<Describe the fix approach and impact. Keep it focused.>

**Key Changes**:
- <Change 1>
- <Change 2>

**Impact**: <What this enables/fixes>

### Checklist
- [x] New/Existing tests provide coverage for changes
```

#### File 2: PR_DETAILS.md

**Purpose**: Detailed context for reviewers (posted as a comment after PR creation)

**Template**:
```markdown
# Detailed Context for PR: <Topic>

This file contains additional context and details for reviewers.

## Files Changed

**Modified**:
- `path/to/file.cpp` (+X/-Y)
  - <detailed description>

**Added**:
- `path/to/test.mlir` - <what it tests>

## Root Cause Details

**Where it failed**: <file:line>
**Why it failed**: <detailed explanation>

## Code/MLIR Transformation Examples

**Before**:
```<language>
<code before>
```

**After**:
```<language>
<code after>
```

## Test Coverage

**Unit Tests**: <list>
**Regression Tests**: <list>
**Models Now Passing**: <list>
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
2. ✅ Two PR files generated:
   - `PR_DESCRIPTION.md` - For PR body
   - `PR_DETAILS.md` - For follow-up comment
3. ✅ Ready to open PR
4. 🔗 Provide gh CLI commands:
   ```bash
   # Create PR with clean description
   gh pr create --repo tenstorrent/<repo> --base main \
     --title "<Title>" \
     --body-file PR_DESCRIPTION.md

   # Post detailed context as comment
   gh pr comment <PR_NUMBER> --body-file PR_DETAILS.md
   ```

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
4. Create branch: `kmabee/sort_f32_workaround_issue_6926`
5. Commit and push changes
6. Generate TWO files:
   - `PR_DESCRIPTION.md` - Clean PR body with just the 4 template sections
   - `PR_DETAILS.md` - Detailed context with code snippets and MLIR examples
7. Provide commands:
   ```bash
   gh pr create --repo tenstorrent/tt-mlir --base main \
     --title "[TTNN] Add f32 input workaround for sort operation" \
     --body-file PR_DESCRIPTION.md

   gh pr comment <PR_NUMBER> --body-file PR_DETAILS.md
   ```

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
- `PR_DESCRIPTION.md` - Clean, concise PR body (for merge commit message)
- `PR_DETAILS.md` - Detailed context with code snippets, MLIR examples, etc. (for comment)

## Tips

- **Reference issue**: Always link to the GitHub issue
- **Credit collaborators**: Mention if someone helped debug
- **Link related PRs**: If there are related changes in other repos
- **Add screenshots**: For UI changes or test output
- **Performance impact**: Mention if there are perf implications
