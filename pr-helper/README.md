# PR Helper Skill

Streamlines the process of preparing pull requests after debugging sessions or feature implementations.

## Usage

```bash
/pr-helper
```

Or simply ask:
- "Help me prepare a PR for this fix"
- "Can you create a PR description?"
- "Let's open a pull request"

## What It Does

1. **Analyzes your changes** - Checks git status, diff, and commits
2. **Gathers context** - Extracts problem, solution, and impact from conversation
3. **Asks for details** - Gets issue number and target repo from you
4. **Creates branch** - Makes `kmabee/<topic>_issue_<XXX>` branch
5. **Commits and pushes** - Stages changes, commits, and pushes to remote
6. **Generates TWO PR files**:
   - `PR_DESCRIPTION.md` - Clean PR body (becomes merge commit message)
   - `PR_DETAILS.md` - Detailed context for posting as a comment

## Example Workflow

After fixing a bug:

```
You: "Can you help me prepare a PR for the ttnn.sort fix?"

Skill:
1. Checks git status: 3 files changed, 2 tests added
2. Extracts from conversation:
   - Problem: ttnn.sort didn't support f32 inputs
   - Fix: Added typecast workaround
   - Tests: Added 2 test files
3. Asks: "What's the GitHub issue number?"
   You: "6926"
4. Creates branch: kmabee/sort_f32_workaround_issue_6926
5. Commits and pushes all changes
6. Generates TWO files:
   - PR_DESCRIPTION.md (clean PR body)
   - PR_DETAILS.md (detailed context for comment)
7. Shows you commands to open PR and post details
```

## PR Template Format

The skill fills in this template:

```markdown
### Ticket
Link to Github Issue

### Problem description
<What was failing and why>

### What's changed
<How it was fixed and what's the impact>

### Checklist
- [x] New/Existing tests provide coverage for changes
```

## Output

Creates TWO files:

### PR_DESCRIPTION.md (clean PR body - becomes merge commit message)

```markdown
### Ticket
https://github.com/tenstorrent/tt-mlir/issues/6926

### Problem description
The ttnn.sort operation only supports BFloat16 or UInt16 input tensors...

### What's changed
Added input type checking in TTNNWorkaroundsPass.cpp...

**Key Changes**:
- Check input element type and insert f32→bf16 typecast
- Apply same conversion to output values tensor

**Impact**: Enables f32-based operations like top-k sorting

### Checklist
- [x] New/Existing tests provide coverage for changes
```

### PR_DETAILS.md (detailed context for posting as comment)

```markdown
# Detailed Context for PR: ttnn.sort f32 Input Workaround

## Files Changed
**Modified**:
- `lib/Dialect/TTNN/IR/TTNNWorkaroundsPass.cpp` (+22/-10)

**Added**:
- `test/ttmlir/Dialect/TTNN/sort/sort_f32_input_workaround.mlir`
- `test/ttmlir/Dialect/TTNN/sort/sort_topk_f32_workaround.mlir`

## Code Before/After
[Detailed code snippets showing the transformation]

## MLIR Transformation
[Examples of MLIR IR before and after the fix]
```

## Features

✅ **Smart context extraction** - Pulls relevant info from conversation
✅ **File change analysis** - Summarizes what changed and why
✅ **Test coverage tracking** - Lists tests added/passing
✅ **Branch management** - Creates, commits, and pushes to branch
✅ **Two-file output** - Clean PR body + detailed context for comment
✅ **Merge commit ready** - PR description becomes the merge commit message
✅ **Ready-to-use output** - Just use gh CLI commands provided

## Tips

- Use after completing a fix or feature
- Make sure all changes are saved (git status should show your changes)
- Have the GitHub issue number ready
- Review the generated PR description before submitting

## Future Enhancements

- [ ] Automatic PR creation via gh CLI
- [ ] Multi-repo PR coordination (e.g., tt-xla + tt-mlir)
- [ ] PR template customization per repo
- [ ] Automatic reviewer assignment
- [ ] Draft PR creation for WIP
