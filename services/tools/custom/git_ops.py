import git
import os
from typing import List, Dict, Optional

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))

def get_repo():
    try:
        return git.Repo(REPO_PATH)
    except git.exc.InvalidGitRepositoryError:
        # Initialize if not exists (optional, but good for safety)
        return git.Repo.init(REPO_PATH)

def git_commit(message: str) -> str:
    """
    Stages all changes and commits them with the provided message.
    """
    try:
        repo = get_repo()
        if not repo.is_dirty(untracked_files=True):
            return "No changes to commit."
        
        repo.git.add(A=True)
        commit = repo.index.commit(message)
        return f"Committed successfully: [{commit.hexsha[:7]}] {message}"
    except Exception as e:
        return f"Git commit failed: {str(e)}"

def git_history(limit: int = 5) -> List[Dict[str, str]]:
    """
    Returns the latest commits.
    """
    try:
        repo = get_repo()
        commits = list(repo.iter_commits(max_count=limit))
        history = []
        for c in commits:
            history.append({
                "hash": c.hexsha[:7],
                "message": c.message.strip(),
                "author": c.author.name,
                "date": c.committed_datetime.isoformat()
            })
        return history
    except Exception as e:
        return [{"error": f"Failed to fetch history: {str(e)}"}]

def git_branch(name: str, action: str = "create") -> str:
    """
    Manages branches. action can be 'create' or 'switch'.
    """
    try:
        repo = get_repo()
        if action == "create":
            new_branch = repo.create_head(name)
            return f"Branch '{name}' created."
        elif action == "switch":
            if name not in repo.heads:
                return f"Branch '{name}' does not exist."
            repo.heads[name].checkout()
            return f"Switched to branch '{name}'."
        else:
            return "Invalid action. Use 'create' or 'switch'."
    except Exception as e:
        return f"Git branch operation failed: {str(e)}"
