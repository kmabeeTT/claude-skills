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
4. **Generates PR description** - Fills in the template with all relevant info
5. **Creates branch** - Makes `kmabee/<topic>_issue_<XXX>` branch
6. **Commits and pushes** - Stages changes, commits, and pushes to remote
7. **Writes PR file** - Creates `PR_<topic>_<date>.md` for easy reference

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
   You: "4567"
4. Creates branch: kmabee/sort_f32_workaround_issue_4567
5. Commits and pushes all changes
6. Generates PR_sort_f32_workaround_2026-02-05.md
7. Shows you how to open the PR
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

Creates a file like `PR_sort_f32_workaround_2026-02-05.md`:

```markdown
# PR: [TTNN] Add f32 input workaround for sort operation

**Branch**: kmabee/sort_f32_workaround_issue_4567
**Issue**: [Link to be filled]

## PR Description for GitHub

### Ticket
https://github.com/tenstorrent/tt-mlir/issues/4567

### Problem description
The ttnn.sort operation only supports BFloat16 or UInt16 input tensors...

### What's changed
Added input type checking in TTNNWorkaroundsPass.cpp...

**Files Modified**:
- `lib/Dialect/TTNN/IR/TTNNWorkaroundsPass.cpp` - Added f32→bf16 conversion
- `test/.../sort_f32_input_workaround.mlir` - New test for workaround

### Checklist
- [x] New/Existing tests provide coverage for changes
```

## Features

✅ **Smart context extraction** - Pulls relevant info from conversation
✅ **File change analysis** - Summarizes what changed and why
✅ **Test coverage tracking** - Lists tests added/passing
✅ **Branch management** - Creates, commits, and pushes to branch
✅ **Ready-to-use output** - Just copy-paste into GitHub
✅ **Future-proof** - Includes gh CLI commands for automation later

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
