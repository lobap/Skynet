"""Git Operations for Skynet Evolution Persistence."""

import os
import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass
from backend.logger import logger

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    git = None

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
SKYNET_TAG = "[SKYNET-EVO]"


@dataclass
class GitResult:
    """Result of a Git operation."""
    success: bool
    message: str = ""
    commit_hash: str = ""
    pushed: bool = False
    error: str = ""


class GitOps:
    """Handles Git operations for evolution persistence."""
    
    def __init__(self, repo_path: str = REPO_PATH):
        self.repo_path = repo_path
        self._repo = None
    
    @property
    def repo(self):
        """Lazy-load Git repository."""
        if self._repo is None:
            if not GIT_AVAILABLE:
                raise ImportError("GitPython not installed")
            try:
                self._repo = git.Repo(self.repo_path)
            except git.exc.InvalidGitRepositoryError:
                self._repo = git.Repo.init(self.repo_path)
        return self._repo
    
    def ensure_config(self) -> bool:
        """Ensure git user config exists."""
        try:
            reader = self.repo.config_reader()
            writer = None
            
            for key, default in [("name", "Skynet"), ("email", "skynet@autonomous.ai")]:
                try:
                    reader.get_value("user", key)
                except Exception:
                    if writer is None:
                        writer = self.repo.config_writer()
                    writer.set_value("user", key, default)
                    logger.info(f"Set git user.{key} to '{default}'")
            
            if writer:
                writer.release()
            return True
        except Exception as e:
            logger.error(f"Git config error: {e}")
            return False
    
    async def auto_commit(self, file_path: str, message: str) -> GitResult:
        """Stage, commit, and push a file."""
        try:
            self.ensure_config()
            rel_path = os.path.relpath(file_path, self.repo_path)
            
            if not os.path.exists(file_path):
                return GitResult(success=False, error=f"File not found: {file_path}")
            
            self.repo.index.add([rel_path])
            full_message = f"{SKYNET_TAG} {message}"
            commit = self.repo.index.commit(full_message)
            commit_hash = commit.hexsha[:7]
            logger.info(f"✅ [{commit_hash}] {full_message}")
            
            pushed = await self._sync()
            
            return GitResult(
                success=True,
                message=full_message,
                commit_hash=commit_hash,
                pushed=pushed
            )
        except Exception as e:
            logger.error(f"Auto-commit failed: {e}")
            return GitResult(success=False, error=str(e))
    
    async def _sync(self) -> bool:
        """Pull and push to origin."""
        try:
            if 'origin' not in [r.name for r in self.repo.remotes]:
                return False
            
            origin = self.repo.remotes.origin
            
            try:
                await asyncio.to_thread(origin.pull, rebase=True)
            except Exception:
                pass  # Pull failures are non-fatal
            
            try:
                await asyncio.to_thread(origin.push)
                logger.info("📤 Pushed to origin")
                return True
            except Exception as e:
                logger.warning(f"Push failed: {e}")
                return False
        except Exception:
            return False
    
    def commit_all(self, message: str) -> str:
        """Stage all and commit."""
        try:
            self.ensure_config()
            if not self.repo.is_dirty(untracked_files=True):
                return "No changes to commit."
            self.repo.git.add(A=True)
            commit = self.repo.index.commit(message)
            return f"[{commit.hexsha[:7]}] {message}"
        except Exception as e:
            return f"Failed: {e}"
    
    def history(self, limit: int = 5) -> List[Dict[str, str]]:
        """Get recent commits."""
        try:
            return [
                {
                    "hash": c.hexsha[:7],
                    "message": c.message.strip(),
                    "author": c.author.name,
                    "date": c.committed_datetime.isoformat()
                }
                for c in self.repo.iter_commits(max_count=limit)
            ]
        except Exception as e:
            return [{"error": str(e)}]
    
    def branch(self, name: str, action: str = "create") -> str:
        """Create or switch branch."""
        try:
            if action == "create":
                self.repo.create_head(name)
                return f"Created: {name}"
            elif action == "switch":
                if name not in self.repo.heads:
                    return f"Branch '{name}' not found"
                self.repo.heads[name].checkout()
                return f"Switched to: {name}"
            return "Invalid action"
        except Exception as e:
            return f"Failed: {e}"


# Singleton instance
_ops = GitOps()


# Public API (backwards compatible)
def get_repo():
    return _ops.repo

def ensure_git_config() -> bool:
    return _ops.ensure_config()

async def auto_commit(file_path: str, message: str) -> Dict[str, Any]:
    result = await _ops.auto_commit(file_path, message)
    return {"success": result.success, "commit_hash": result.commit_hash, 
            "message": result.message, "pushed": result.pushed, "error": result.error}

def git_commit(message: str) -> str:
    return _ops.commit_all(message)

def git_history(limit: int = 5) -> List[Dict[str, str]]:
    return _ops.history(limit)

def git_branch(name: str, action: str = "create") -> str:
    return _ops.branch(name, action)
