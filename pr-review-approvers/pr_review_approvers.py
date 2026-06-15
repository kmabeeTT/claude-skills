#!/usr/bin/env python3
"""Given a PR, report which code-owner TEAMS are still waiting to review, and
for each team list the top approvers based on the team's last N reviewed PRs.

Usage:
    pr_review_approvers.py <pr-number-or-url> [--repo owner/name] [--prs 10] [--scan 200]

"Top approvers per team" = among the most recent N PRs that at least one member
of the team approved, count APPROVED reviews per member and rank them. This
answers "who normally signs off for this group" without needing CODEOWNERS path
matching (an approval by a team member is the signal the team's review was met).

Requires the `gh` CLI, authenticated with org read access.
"""
import argparse
import base64
import json
import re
import subprocess
import sys
from collections import defaultdict


def gh(args, parse_json=True):
    out = subprocess.run(
        ["gh"] + args, capture_output=True, text=True
    )
    if out.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{out.stderr}")
    return json.loads(out.stdout) if parse_json else out.stdout


def gh_graphql(query, variables):
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-F", f"{k}={v}"]
    return gh(args)


def parse_pr(arg, repo_flag):
    """Return (owner, repo, number)."""
    m = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", arg)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    if repo_flag:
        owner, repo = repo_flag.split("/")
        return owner, repo, int(arg)
    # Fall back to the current repo.
    info = gh(["repo", "view", "--json", "owner,name"])
    return info["owner"]["login"], info["name"], int(arg)


def team_members(org, slug):
    return [
        m["login"]
        for m in gh(["api", f"orgs/{org}/teams/{slug}/members", "--paginate"])
    ]


def outstanding_teams(owner, repo, number):
    data = gh(["api", f"repos/{owner}/{repo}/pulls/{number}/requested_reviewers"])
    return [t["slug"] for t in data.get("teams", [])]


def existing_reviews(owner, repo, number):
    """Map login -> latest review state for this PR."""
    revs = gh(["api", f"repos/{owner}/{repo}/pulls/{number}/reviews", "--paginate"])
    latest = {}
    for r in revs:
        login = (r.get("user") or {}).get("login")
        if login:
            latest[login] = r["state"]
    return latest


def recent_pr_reviews(owner, repo, scan):
    """Fetch up to `scan` most-recently-updated merged PRs with their reviews.

    Returns a list of dicts: {number, approvers: [logins...]} newest first.
    """
    query = """
    query($owner:String!, $repo:String!, $cursor:String) {
      repository(owner:$owner, name:$repo) {
        pullRequests(states:MERGED, first:50,
                     orderBy:{field:UPDATED_AT, direction:DESC}, after:$cursor) {
          pageInfo { hasNextPage endCursor }
          nodes {
            number
            reviews(first:100) { nodes { state author { login } } }
          }
        }
      }
    }
    """
    prs, cursor = [], None
    while len(prs) < scan:
        variables = {"owner": owner, "repo": repo}
        if cursor:
            variables["cursor"] = cursor
        data = gh_graphql(query, variables)
        conn = data["data"]["repository"]["pullRequests"]
        for node in conn["nodes"]:
            approvers = []
            for rev in node["reviews"]["nodes"]:
                if rev["state"] == "APPROVED" and rev["author"]:
                    approvers.append(rev["author"]["login"])
            prs.append({"number": node["number"], "approvers": approvers})
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
    return prs[:scan]


def changed_files(owner, repo, number):
    files = gh(
        ["api", f"repos/{owner}/{repo}/pulls/{number}/files", "--paginate"]
    )
    return [f["filename"] for f in files]


def fetch_codeowners(owner, repo):
    """Return CODEOWNERS text, checking the locations GitHub honors in order."""
    for path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        out = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/contents/{path}", "--jq", ".content"],
            capture_output=True,
            text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            return base64.b64decode(out.stdout).decode("utf-8")
    return ""


def _pattern_to_regex(pattern):
    """Translate a CODEOWNERS (gitignore-style) pattern to a compiled regex
    matched against a repo-relative path with no leading slash."""
    dir_only = pattern.endswith("/")
    core = pattern[:-1] if dir_only else pattern
    # Anchored if a slash appears at the start or middle (gitignore rule);
    # otherwise the pattern matches a basename at any depth.
    anchored = core.startswith("/") or "/" in core
    core = core.lstrip("/")

    body, i, n = "", 0, len(core)
    while i < n:
        c = core[i]
        if c == "*":
            if i + 1 < n and core[i + 1] == "*":
                body += ".*"
                i += 2
                continue
            body += "[^/]*"
        elif c == "?":
            body += "[^/]"
        else:
            body += re.escape(c)
        i += 1

    if dir_only:
        body += "/.*"          # directory pattern: everything beneath it
    else:
        body += "(/.*)?"       # match the path itself or, if a dir, its contents
    prefix = "^" if anchored else "^(.*/)?"
    return re.compile(prefix + body + "$")


def parse_codeowners(text):
    """Return ordered [(regex, [owners...])]; later entries take precedence."""
    rules = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        pattern, owners = parts[0], parts[1:]
        rules.append((_pattern_to_regex(pattern), owners))
    return rules


def owners_for_file(path, rules):
    """Last matching rule wins (GitHub semantics)."""
    owners = []
    for regex, os_ in rules:
        if regex.match(path):
            owners = os_
    return owners


def files_by_team(files, rules, org):
    """Map team-slug -> [files], plus files owned only by individual users.
    A team owner looks like @org/team-slug."""
    by_team = defaultdict(list)
    by_user = defaultdict(list)
    team_prefix = f"@{org}/"
    for f in files:
        for owner in owners_for_file(f, rules):
            if owner.startswith(team_prefix):
                by_team[owner[len(team_prefix):]].append(f)
            elif owner.startswith("@"):
                by_user[owner[1:]].append(f)
    return by_team, by_user


def top_approvers_for_team(members, prs, last_n):
    """Among the most recent `last_n` PRs approved by any team member, tally
    approvals per member. Returns (ranked list of (login, count), pr_numbers)."""
    member_set = set(members)
    counts = defaultdict(int)
    used_prs = []
    for pr in prs:  # newest first
        team_approvers = [a for a in set(pr["approvers"]) if a in member_set]
        if not team_approvers:
            continue
        used_prs.append(pr["number"])
        for a in team_approvers:
            counts[a] += 1
        if len(used_prs) >= last_n:
            break
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked, used_prs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", help="PR number or URL")
    ap.add_argument("--repo", help="owner/name (if PR given as bare number for another repo)")
    ap.add_argument("--prs", type=int, default=10, help="last N reviewed PRs per team (default 10)")
    ap.add_argument("--scan", type=int, default=200, help="how many recent merged PRs to scan (default 200)")
    ap.add_argument("--teams", help="comma-separated team slugs to analyze instead of the PR's outstanding requests")
    args = ap.parse_args()

    owner, repo, number = parse_pr(args.pr, args.repo)
    org = owner

    teams = args.teams.split(",") if args.teams else outstanding_teams(owner, repo, number)
    reviews = existing_reviews(owner, repo, number)

    # Map this PR's changed files to code-owner teams via CODEOWNERS.
    files = changed_files(owner, repo, number)
    rules = parse_codeowners(fetch_codeowners(owner, repo))
    by_team, by_user = files_by_team(files, rules, org) if rules else ({}, {})

    print(f"PR {owner}/{repo}#{number}  ({len(files)} files changed)")
    approved_by = [u for u, s in reviews.items() if s == "APPROVED"]
    if approved_by:
        print(f"Already approved by: {', '.join(sorted(approved_by))}")

    if not teams:
        print("\nNo outstanding code-owner TEAM reviews. ✅")
    else:
        print(f"\nWaiting on code-owner review from {len(teams)} team(s): {', '.join(teams)}")

    print(f"Scanning last {args.scan} merged PRs for approval history...\n")
    prs = recent_pr_reviews(owner, repo, args.scan)

    for slug in teams:
        members = team_members(org, slug)
        ranked, used = top_approvers_for_team(members, prs, args.prs)
        print(f"── {slug} ({len(members)} members) ──")
        owned = by_team.get(slug, [])
        if rules:
            if owned:
                print(f"   Owns {len(owned)} changed file(s):")
                for f in owned:
                    print(f"       {f}")
            else:
                print("   Owns no changed files (requested via broader rule or removed match).")
        already = [m for m in members if reviews.get(m) == "APPROVED"]
        if already:
            print(f"   ✅ already approved this PR: {', '.join(already)}")
        if not ranked:
            print(f"   No approvals found from this team in the last {args.scan} PRs.")
        else:
            print(f"   Top approvers (over last {len(used)} PRs this team reviewed):")
            for login, cnt in ranked[:5]:
                print(f"     {cnt:>2} approvals  {login}")
        print()

    # Surface any changed files owned by teams NOT in the analyzed set, plus
    # files owned only by individual users — so the ownership picture is whole.
    other_teams = {t: fs for t, fs in by_team.items() if t not in teams}
    if other_teams:
        print("Other code-owner teams on changed files:")
        for slug, fs in sorted(other_teams.items()):
            print(f"   {slug}: {', '.join(fs)}")
    if by_user:
        print("Individual code owners on changed files:")
        for user, fs in sorted(by_user.items()):
            print(f"   @{user}: {', '.join(fs)}")


if __name__ == "__main__":
    main()
