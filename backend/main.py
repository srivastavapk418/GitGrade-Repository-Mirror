from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import re
import os

app = FastAPI(title="GitGrade – Repository Mirror")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoInput(BaseModel):
    repo_url: str

def parse_repo(url: str):
    parts = url.rstrip("/").split("/")
    return parts[-2], parts[-1]

def gh_get(url):
    headers = {}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"
    return requests.get(url, headers=headers)

def extract_repo_signals(owner, repo):
    base = f"https://api.github.com/repos/{owner}/{repo}"

    repo_data = gh_get(base).json()
    commits = gh_get(base + "/commits?per_page=100").json()
    languages = gh_get(base + "/languages").json()

    readme_resp = gh_get(base + "/readme")
    readme_text = ""
    if readme_resp.status_code == 200:
        import base64
        readme_text = base64.b64decode(readme_resp.json()["content"]).decode(errors="ignore")

    tree = gh_get(base + "/git/trees/main?recursive=1").json()
    files = tree.get("tree", []) if isinstance(tree, dict) else []

    return {
        "stars": repo_data.get("stargazers_count", 0),
        "files_count": len([f for f in files if f.get("type") == "blob"]),
        "has_src": any("src/" in f.get("path", "") for f in files),
        "has_tests": any(re.search(r"test|__tests__", f.get("path",""), re.I) for f in files),
        "readme_len": len(readme_text),
        "readme_has_install": "install" in readme_text.lower(),
        "readme_has_usage": "usage" in readme_text.lower(),
        "commit_count": len(commits) if isinstance(commits, list) else 0,
        "languages": list(languages.keys()),
        "has_ci": any(".github/workflows" in f.get("path","") for f in files),
        "has_env_example": any(".env.example" in f.get("path","") for f in files),
    }

def score_repo(s):
    scores = {}

    doc = 0
    if s["readme_len"] > 0: doc += 10
    if s["readme_len"] > 300: doc += 10
    if s["readme_has_install"]: doc += 5
    if s["readme_has_usage"]: doc += 5
    scores["documentation"] = doc

    code = 10
    if s["has_src"]: code += 10
    if s["files_count"] >= 10: code += 5
    if s["files_count"] >= 30: code += 5
    scores["code_quality"] = code

    scores["testing"] = 20 if s["has_tests"] else 0

    git = 5
    if s["commit_count"] >= 5: git += 5
    if s["commit_count"] >= 20: git += 10
    scores["git_practices"] = git

    real = 0
    if s["has_env_example"]: real += 5
    if s["has_ci"]: real += 5
    if len(s["languages"]) > 1: real += 5
    scores["real_world"] = real

    total = sum(scores.values())
    return scores, min(total, 100)

def generate_feedback(scores):
    strengths, gaps, roadmap = [], [], []

    if scores["documentation"] >= 20:
        strengths.append("clear documentation")
    else:
        gaps.append("insufficient documentation")
        roadmap.append("Add a detailed README with installation and usage")

    if scores["testing"] == 0:
        gaps.append("no automated tests")
        roadmap.append("Introduce unit tests using Jest or PyTest")

    if scores["git_practices"] < 10:
        gaps.append("limited commit history")
        roadmap.append("Commit more frequently with meaningful messages")

    if scores["real_world"] < 10:
        gaps.append("missing production-readiness signals")
        roadmap.append("Add CI/CD and environment configuration examples")

    summary = (
        f"The repository shows {', '.join(strengths) if strengths else 'basic structure'}, "
        f"but has gaps such as {', '.join(gaps)}."
    )

    return summary, roadmap

@app.post("/analyze")
def analyze_repo(data: RepoInput):
    owner, repo = parse_repo(data.repo_url)

    signals = extract_repo_signals(owner, repo)
    scores, total = score_repo(signals)

    level = "Beginner"
    if total >= 70: level = "Advanced"
    elif total >= 40: level = "Intermediate"

    summary, roadmap = generate_feedback(scores)

    return {
        "score": total,
        "level": level,
        "summary": summary,
        "roadmap": roadmap,
        "signals_used": signals
    }
