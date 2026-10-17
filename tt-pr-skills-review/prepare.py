#!/usr/bin/env python3
"""Stage a local run of tt-metal's Skills reviewers on a branch.

tt-metal runs two gh-aw reviewers on `pull_request` opened / ready_for_review only
(never on drafts, never on a base other than main):
  .github/workflows/mattpocock-skills-reviewer.md
  .github/workflows/tenstorrent-skills-reviewer.md
This script reproduces what their pre-agent steps do, from local git instead of a PR:

  - reads each workflow's frontmatter (pinned skills, path filters) and prompt
    from the tt-metal tree at --workflows-ref (default origin/main, i.e. what the
    bot would run),
  - clones the pinned skills repos once into a cache and links the skills in,
  - writes the pre-fetched data the prompt expects (pr-meta.json, pr-diff.patch
    capped at 2000 lines, pr-review-comments.json, and the split-check inputs for
    wide diffs),
  - writes a PROMPT.md per reviewer: the workflow prompt with its paths rewritten
    to this run directory and its GitHub outputs replaced by a local FINDINGS.md.

It never writes to GitHub. With --pr N it reads that PR's existing review comments
(read-only gh) so the review skips what is already said.

Usage:
  prepare.py --head kmabee/my-branch [--base origin/main] [--tree /path/to/tt-metal]
             [--body-file PR_DRAFT_X.md | --title T --body-text B] [--pr N]
             [--out-root DIR] [--only tenstorrent|mattpocock] [--all]

Prints the run directory and the PROMPT.md of each reviewer that would fire.
"""

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import sys

import yaml

REVIEWERS = {
    "tenstorrent": "tenstorrent-skills-reviewer",
    "mattpocock": "mattpocock-skills-reviewer",
}
DIFF_EXCLUDES = ["**/*.lock.yml", "**/generated/**", "**/dist/**", "**/build/**"]
DIFF_MAX_LINES = 2000
SPLIT_MIN_CHANGED_FILES = 20
REPO = "tenstorrent/tt-metal"
CACHE = os.path.expanduser("~/.cache/tt-pr-skills-review")


def sh(args, cwd=None, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"command failed ({r.returncode}): {' '.join(args)}\n{r.stderr.strip()}")
    return r


def git(tree, *args, check=True):
    return sh(["git", "-C", tree, *args], check=check).stdout


def read_workflow(tree, ref, name):
    text = git(tree, "show", f"{ref}:.github/workflows/{name}.md")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        sys.exit(f"{name}.md: no frontmatter")
    front = yaml.safe_load(m.group(1))
    body = m.group(2)
    # The prompt ends where the pr-triage agent definition starts.
    parts = re.split(r"^## agent: `pr-triage`\s*$", body, maxsplit=1, flags=re.M)
    return front, parts[0], (parts[1] if len(parts) > 1 else "")


def path_matches(path, pattern):
    # GitHub's path filters: `*` stops at `/`, `**` crosses it. fnmatch's `*`
    # crosses `/`, which over-matches `"*.md"` (root only); handle that case.
    if "/" not in pattern and "**" not in pattern:
        return "/" not in path and fnmatch.fnmatch(path, pattern)
    return fnmatch.fnmatch(path, pattern.replace("**/", "*").replace("/**", "/*"))


def would_fire(front, files):
    pr = (front.get("on") or front.get(True) or {}).get("pull_request", {})
    if "paths" in pr:
        hit = False
        for f in files:
            inc = None
            for p in pr["paths"]:
                neg = p.startswith("!")
                if path_matches(f, p[1:] if neg else p):
                    inc = not neg
            hit = hit or bool(inc)
        return hit
    if "paths-ignore" in pr:
        return any(not any(path_matches(f, p) for p in pr["paths-ignore"]) for f in files)
    return True


def fetch_skill(spec):
    """`owner/repo/sub/path@sha` -> local dir holding that skill's SKILL.md."""
    loc, sha = spec.rsplit("@", 1)
    owner, repo, *sub = loc.split("/")
    clone = os.path.join(CACHE, "repos", f"{owner}__{repo}@{sha[:12]}")
    if not os.path.isdir(os.path.join(clone, ".git")):
        os.makedirs(os.path.dirname(clone), exist_ok=True)
        tmp = f"{clone}.partial-{os.getpid()}"
        sh(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", f"https://github.com/{owner}/{repo}.git", tmp])
        sh(["git", "-C", tmp, "checkout", "-q", sha])
        os.rename(tmp, clone)
    direct = os.path.join(clone, *sub)
    if sub and os.path.isfile(os.path.join(direct, "SKILL.md")):
        return direct
    # `gh skill` resolves a bare name (mattpocock/skills/tdd) by searching the repo;
    # skip plugin copies so the canonical skills/ tree wins.
    name = sub[-1] if sub else repo
    hits = []
    for root, dirs, fs in os.walk(clone):
        dirs[:] = [d for d in dirs if d != ".git"]
        if os.path.basename(root) == name and "SKILL.md" in fs:
            hits.append(root)
    hits.sort(key=lambda p: ("/plugins/" in p, "/deprecated/" in p, len(p)))
    if not hits:
        sys.exit(f"skill {spec}: no {name}/SKILL.md in {clone}")
    return hits[0]


def parse_body_file(path):
    """PR draft convention: header notes, `**Title:** ...`, then `**Body**`; the body
    ends at a `---` line (follow-up comments come after it)."""
    text = open(path).read()
    t = re.search(r"^\*\*Title:\*\*\s*(.+)$", text, re.M)
    b = re.search(r"^\*\*Body\*\*\s*$", text, re.M)
    if not t or not b:
        sys.exit(f"{path}: expected a **Title:** line and a **Body** line")
    body = text[b.end():]
    body = re.split(r"^---\s*$", body, maxsplit=1, flags=re.M)[0]
    return t.group(1).strip(), body.strip()


def adapt_prompt(prompt, triage, run, rdir, skills_dir, meta, tree, head_sha, reviewer):
    data = os.path.join(run, "data")
    out = os.path.join(rdir, "FINDINGS.md")
    triage_file = os.path.join(rdir, "TRIAGE.md")
    subs = {
        "${{ github.repository }}": REPO,
        "${{ github.event.pull_request.number }}": str(meta["number"]),
        "${{ github.event.pull_request.title }}": meta["title"],
        "${{ github.actor }}": meta["author"]["login"],
    }
    for k, v in subs.items():
        prompt = prompt.replace(k, v)
        triage = triage.replace(k, v)
    for k, v in (("/tmp/gh-aw/agent/", data + "/"), ("/tmp/gh-aw/agent", data), (".github/skills", skills_dir)):
        prompt = prompt.replace(k, v)
        triage = triage.replace(k, v)
    with open(triage_file, "w") as f:
        f.write(triage.strip() + "\n")

    preamble = f"""# Local run of the `{REVIEWERS[reviewer]}` workflow

You are running tt-metal's `{REVIEWERS[reviewer]}` reviewer **locally**, before the PR is opened or undrafted. Follow the workflow prompt below as written, with these substitutions. They override anything below that conflicts.

- **Pre-fetched data** is in `{data}/` (already substituted below). Skills are installed under `{skills_dir}/` (already substituted below).
- **Source context:** the diff is `{meta['baseRefName']}...{meta['headRefName']}` at `{head_sha}`. The checkout at `{tree}` may be at a different commit, so read whole files with `git -C {tree} show {head_sha}:<path>`, not from the working tree.
- **Triage:** "invoke the `pr-triage` agent" means: do the routing in `{triage_file}` yourself, inline (don't skip it), and write its JSON to `{rdir}/triage.json` before reviewing. Name the selected skills in the overall review. Use the fallback only if you can't produce valid JSON.
- **No GitHub writes.** You have no safe-outputs. Never call `gh` to post, comment, review or edit. Instead, write everything to `{out}`:
  - each `create-pull-request-review-comment` becomes a section `### <path>:<line>` followed by the comment body exactly as you would post it;
  - `submit_pull_request_review` becomes a section `## Overall review` with the review body;
  - `add-comment` (optional summary) becomes `## Summary comment`;
  - `noop` becomes a single line `NOOP: <reason>`;
  - `create_check_run` is skipped.
- Keep every other rule: the 10-comment limit, changed lines only, severities, the evidence rule and the false-positive guards.
- When you are done, reply with only the path of `{out}` and a one-line count of findings by severity.

---

"""
    with open(os.path.join(rdir, "PROMPT.md"), "w") as f:
        f.write(preamble + prompt.strip() + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", default=os.getcwd(), help="tt-metal checkout (default: cwd)")
    ap.add_argument("--head", default="HEAD", help="branch or sha under review (default: HEAD)")
    ap.add_argument("--base", default="origin/main", help="PR base (default: origin/main)")
    ap.add_argument("--workflows-ref", default="origin/main", help="where to read the reviewer workflows from")
    ap.add_argument("--body-file", help="PR draft .md with **Title:** / **Body** sections")
    ap.add_argument("--title", help="PR title (overrides --body-file's)")
    ap.add_argument("--body-text", help="PR body (overrides --body-file's)")
    ap.add_argument("--pr", type=int, help="existing PR number: read its review comments (read-only)")
    ap.add_argument("--out-root", default=os.path.join(CACHE, "runs"))
    ap.add_argument("--only", choices=sorted(REVIEWERS), action="append", help="run only this reviewer")
    ap.add_argument("--all", action="store_true", help="prepare reviewers even if their path filter would skip the diff")
    a = ap.parse_args()

    tree = os.path.abspath(a.tree)
    head_sha = git(tree, "rev-parse", a.head).strip()
    base_sha = git(tree, "merge-base", a.base, head_sha).strip()
    head_name = a.head if a.head != "HEAD" else git(tree, "rev-parse", "--abbrev-ref", "HEAD").strip()
    head_name = re.sub(r"^origin/", "", head_name)
    base_name = re.sub(r"^origin/", "", a.base)

    title, body = (parse_body_file(a.body_file) if a.body_file else (None, ""))
    title = a.title or title or git(tree, "log", "-1", "--format=%s", head_sha).strip()
    body = a.body_text if a.body_text is not None else body

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run = os.path.join(os.path.abspath(a.out_root), f"{re.sub(r'[^A-Za-z0-9._-]+', '_', head_name)}_{stamp}")
    data = os.path.join(run, "data")
    os.makedirs(data)

    # --- pre-fetched PR data (mirrors the workflows' pre-agent steps) ---
    excl = [f":(exclude,glob){p}" for p in DIFF_EXCLUDES]
    full = git(tree, "diff", f"{base_sha}...{head_sha}", "--", ".", *excl)
    with open(os.path.join(data, "pr-diff.full"), "w") as f:
        f.write(full)
    lines = full.splitlines(keepends=True)
    with open(os.path.join(data, "pr-diff.patch"), "w") as f:
        f.writelines(lines[:DIFF_MAX_LINES])

    files, adds, dels = [], 0, 0
    for row in git(tree, "diff", "--numstat", f"{base_sha}...{head_sha}").splitlines():
        ad, de, path = row.split("\t", 2)
        ad, de = (int(ad) if ad != "-" else 0), (int(de) if de != "-" else 0)
        files.append({"path": path, "additions": ad, "deletions": de})
        adds, dels = adds + ad, dels + de
    login = sh(["gh", "api", "user", "--jq", ".login"], check=False).stdout.strip() or git(tree, "config", "user.name").strip()
    meta = {
        "number": a.pr if a.pr else "(local, not opened)",
        "title": title,
        "body": body,
        "baseRefName": base_name,
        "headRefName": head_name,
        "headRefOid": head_sha,
        "additions": adds,
        "deletions": dels,
        "changedFiles": len(files),
        "files": files[:100],  # gh pr view caps at 100; the split check uses pr-files.txt
        "author": {"login": login},
        "reviewRequests": [],
    }
    json.dump(meta, open(os.path.join(data, "pr-meta.json"), "w"), indent=1)

    comments = []
    if a.pr:
        r = sh(["gh", "api", f"repos/{REPO}/pulls/{a.pr}/comments", "--paginate", "--jq",
                ".[] | {id, path, line: (.line // .original_line), body: .body[:200], user: .user.login}"], check=False)
        comments = [json.loads(x) for x in r.stdout.splitlines() if x.strip()]
    json.dump(comments, open(os.path.join(data, "pr-review-comments.json"), "w"), indent=1)
    open(os.path.join(data, "pr-data-head-sha.txt"), "w").write(head_sha + "\n")

    # Split check inputs (tenstorrent reviewer, wide diffs only).
    split = "skipped (< %d files)" % SPLIT_MIN_CHANGED_FILES
    if len(files) >= SPLIT_MIN_CHANGED_FILES:
        co = git(tree, "show", f"{a.base}:.github/CODEOWNERS", check=False)
        if co.strip():
            open(os.path.join(data, "CODEOWNERS.base"), "w").write(co)
            open(os.path.join(data, "pr-files.txt"), "w").write("".join(f["path"] + "\n" for f in files))
            rules = sh(["gh", "api", f"repos/{REPO}/rules/branches/{base_name}"], check=False).stdout or "[]"
            try:
                prs = [x["parameters"] for x in json.loads(rules) if x.get("type") == "pull_request"]
            except (ValueError, KeyError, TypeError):
                prs = []
            ctx = {
                "base": base_name, "codeowners_path": ".github/CODEOWNERS", "head_sha": head_sha,
                "changed_files": len(files), "files_fetched": len(files),
                "required_approvals": max([p.get("required_approving_review_count", 0) for p in prs] or [0]),
                "owner_review_required": any(p.get("require_code_owner_review") for p in prs),
                "author": "@" + login, "already_approved": "", "requested_reviewers": [],
            }
            json.dump(ctx, open(os.path.join(data, "pr-split-context.json"), "w"), indent=1)
            open(os.path.join(data, "split-check.enabled"), "w").close()
            split = "enabled"
        else:
            split = f"disabled (no CODEOWNERS on {a.base})"

    # --- reviewers ---
    paths = [f["path"] for f in files]
    print(f"run dir: {run}")
    print(f"diff: {base_name}...{head_name} ({head_sha[:11]}), {len(files)} files, +{adds}/-{dels}, "
          f"{len(lines)} diff lines{' (patch capped at %d)' % DIFF_MAX_LINES if len(lines) > DIFF_MAX_LINES else ''}")
    print(f"title: {title}")
    print(f"split check: {split}")
    if base_name != "main":
        print(f"note: base is {base_name}; on GitHub neither reviewer fires on a non-main base")
    for key in a.only or sorted(REVIEWERS):
        front, prompt, triage = read_workflow(tree, a.workflows_ref, REVIEWERS[key])
        fires = would_fire(front, paths)
        if not fires and not a.all:
            print(f"{key}: SKIP (its path filter would not trigger on this diff; --all to run anyway)")
            continue
        rdir = os.path.join(run, key)
        skills_dir = os.path.join(rdir, "skills")
        os.makedirs(skills_dir)
        for spec in front.get("skills", []):
            src = fetch_skill(spec)
            os.symlink(src, os.path.join(skills_dir, os.path.basename(src)))
        adapt_prompt(prompt, triage, run, rdir, skills_dir, meta, tree, head_sha, key)
        print(f"{key}: {os.path.join(rdir, 'PROMPT.md')} ({len(front.get('skills', []))} skills, model {front.get('model')})")


if __name__ == "__main__":
    main()
