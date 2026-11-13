#!/usr/bin/env python3
"""Arautos das Torres: estado dos PRs e dos deploys dos domínios, via GitHub.

Uso: python3 arautos.py                 -> JSON (e guarda em ~/.cache/tomo-rubro/arautos.json)
     python3 arautos.py --repos a,b      -> só esses domínios (pelo nome curto), fundidos
                                            ao último resultado guardado (vigília rápida)

Os domínios vêm de dominios.json (ao lado deste arquivo): ["Visio-ai/permissions-wc", ...].
Uma só consulta GraphQL (gh api graphql) traz, por domínio:
  - os PRs abertos: provas (statusCheckRollup), revisão, rascunho, autor, base;
  - o deploy mais recente de cada ambiente (Deployments do GitHub) e seu estado;
  - a ponta de main e de rc, para dizer se o ambiente está atrás da branch;
  - quantos commits rc tem que main ainda não tem (aguardam a torre principal).
E, pela API REST de Actions, os workflows em curso ou na fila de cada domínio, com o
job e o passo em que estão ("encantamentos em curso").
Só lê; nada no GitHub é alterado.
"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache/tomo-rubro/arautos.json"
BOTS = ("dependabot", "renovate", "github-actions")

REPO = """
  r%(i)d: repository(owner: "%(owner)s", name: "%(name)s") {
    nameWithOwner url
    pullRequests(states: OPEN, first: 30, orderBy: {field: UPDATED_AT, direction: DESC}) { nodes {
      number title url isDraft author { login } headRefName baseRefName reviewDecision mergeable updatedAt
      commits(last: 1) { nodes { commit { statusCheckRollup { state } } } } } }
    deployments(first: 30, orderBy: {field: CREATED_AT, direction: DESC}) { nodes {
      environment createdAt ref { name } commit { oid abbreviatedOid messageHeadline }
      latestStatus { state createdAt logUrl } } }
    main: ref(qualifiedName: "refs/heads/main") {
      target { ... on Commit { oid committedDate } } compare(headRef: "rc") { aheadBy } }
    rc: ref(qualifiedName: "refs/heads/rc") { target { ... on Commit { oid committedDate } } }
  }"""


def gh_json(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout else None


def runs(full):
    """Workflows of one domain that are queued or running, with the job and step they are on."""
    d = gh_json(f"repos/{full}/actions/runs?per_page=20") or {}
    out = []
    for w in d.get("workflow_runs") or []:
        if w.get("status") == "completed":
            continue
        run = {"id": w["id"], "name": w.get("name"), "branch": w.get("head_branch"), "event": w.get("event"),
               "title": w.get("display_title"), "status": w.get("status"), "url": w.get("html_url"),
               "started": w.get("run_started_at") or w.get("created_at"), "jobs_done": 0, "jobs": 0}
        jobs = (gh_json(f"repos/{full}/actions/runs/{w['id']}/jobs?per_page=50") or {}).get("jobs") or []
        run["jobs"] = len(jobs)
        run["jobs_done"] = sum(1 for j in jobs if j.get("status") == "completed")
        run["failed"] = any(j.get("conclusion") == "failure" for j in jobs)
        cur = next((j for j in jobs if j.get("status") == "in_progress"), None) \
            or next((j for j in jobs if j.get("status") in ("queued", "waiting", "pending")), None)
        if cur:
            steps = cur.get("steps") or []
            step = next((x for x in steps if x.get("status") == "in_progress"), None)
            done = sum(1 for x in steps if x.get("status") == "completed")
            run["job"] = {"name": cur.get("name"), "status": cur.get("status"), "url": cur.get("html_url"),
                          "step": step.get("name") if step else None,
                          "n": done + 1 if step else done, "of": len(steps)}
        out.append(run)
    return out


def main():
    repos = json.loads((HERE / "dominios.json").read_text())
    only = None
    if "--repos" in sys.argv:
        only = set(sys.argv[sys.argv.index("--repos") + 1].split(","))
        repos = [r for r in repos if r.split("/", 1)[1] in only]
    pool = ThreadPoolExecutor(max_workers=6)  # the Actions calls run while the GraphQL query does
    pending = {full: pool.submit(runs, full) for full in repos}
    parts = []
    for i, full in enumerate(repos):
        owner, name = full.split("/", 1)
        parts.append(REPO % {"i": i, "owner": owner, "name": name})
    query = "query { viewer { login }" + "".join(parts) + "\n}"
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"], capture_output=True, text=True, timeout=60)
    try:
        data = json.loads(r.stdout)  # a partial answer (one domain without rc) still carries the data
    except ValueError:
        print(json.dumps({"error": (r.stderr or "o GitHub não respondeu").strip()[:400], "at": time.time()}))
        return
    d = data.get("data") or {}
    active = {}
    for full, fut in pending.items():
        try:
            active[full] = fut.result(timeout=60)
        except Exception:
            active[full] = []
    pool.shutdown(wait=False)
    viewer = (d.get("viewer") or {}).get("login")
    out = []
    for i, full in enumerate(repos):
        repo = d.get(f"r{i}")
        if not repo:
            out.append({"name": full.split("/", 1)[1], "full": full, "error": "domínio inacessível"})
            continue
        prs = []
        for p in repo["pullRequests"]["nodes"]:
            author = (p.get("author") or {}).get("login") or "?"
            roll = (((p["commits"]["nodes"] or [{}])[0].get("commit") or {}).get("statusCheckRollup") or {}).get("state")
            prs.append({
                "number": p["number"], "title": p["title"], "url": p["url"], "draft": p["isDraft"],
                "author": author, "mine": author == viewer, "bot": any(b in author.lower() for b in BOTS),
                "base": p["baseRefName"], "head": p["headRefName"], "review": p["reviewDecision"],
                "mergeable": p["mergeable"], "checks": roll, "updated": p["updatedAt"],
            })
        heads = {}
        for b in ("main", "rc"):
            t = (repo.get(b) or {}).get("target") or {}
            if t.get("oid"):
                heads[b] = {"oid": t["oid"], "date": t.get("committedDate")}
        envs = {}
        for x in repo["deployments"]["nodes"]:
            env = x["environment"]
            if env in envs:
                continue
            st = x.get("latestStatus") or {}
            ref = (x.get("ref") or {}).get("name")
            commit = x.get("commit") or {}
            branch_head = heads.get(ref, {}).get("oid")
            envs[env] = {
                "state": st.get("state") or "PENDING", "at": st.get("createdAt") or x["createdAt"],
                "ref": ref, "oid": commit.get("abbreviatedOid"), "headline": commit.get("messageHeadline"),
                "log": st.get("logUrl"), "behind": bool(branch_head and commit.get("oid") and branch_head != commit["oid"]),
            }
        main_ref = repo.get("main") or {}
        out.append({
            "name": repo["nameWithOwner"].split("/", 1)[1], "full": repo["nameWithOwner"], "url": repo["url"],
            "prs": prs, "envs": envs, "heads": heads, "runs": active.get(full) or [],
            "rc_ahead": (main_ref.get("compare") or {}).get("aheadBy") if heads.get("rc") else None,
        })
    result = {"at": time.time(), "viewer": viewer, "repos": out}
    if only is not None:  # a quick watch: fold these domains into the last full answer
        try:
            prev = json.loads(CACHE.read_text())
            fresh = {r["name"]: r for r in out}
            prev["repos"] = [fresh.get(r["name"], r) for r in prev.get("repos", [])]
            prev["at_quick"] = result["at"]
            prev["viewer"] = prev.get("viewer") or viewer
            result = prev
        except (OSError, ValueError):
            pass
    if data.get("errors"):
        result["warnings"] = [e.get("message", "")[:200] for e in data["errors"]][:5]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False))
    os.replace(tmp, CACHE)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"[:400], "at": time.time()}))
        sys.exit(0)
