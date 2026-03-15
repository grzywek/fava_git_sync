"""Git sync for Fava"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
import subprocess

from fava.ext import FavaExtensionBase, extension_endpoint
from flask.wrappers import Response


class FavaGitSync(FavaExtensionBase):
    """Git sync for Fava"""

    has_js_module = True

    last_remote_check = None
    remote_check_delay_seconds = 30

    cached_local_ahead = 0
    cached_remote_ahead = 0

    @extension_endpoint("sync", ["GET"])
    def sync(self) -> Response:
        # Auto-commit if there are uncommitted changes
        has_dirty = self._is_dirty()
        if has_dirty:
            st = self._run(["git", "add", "-A"])
            if st["returncode"] != 0:
                return self._error_response("git add -A failed", st)

            now = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
            st = self._run(["git", "commit", "-m", now])
            if st["returncode"] != 0:
                return self._error_response("git commit failed", st)

        # Pull then push
        st = self._run(["git", "pull", "--rebase"])
        if st["returncode"] != 0:
            return self._error_response("git pull --rebase failed", st)

        st = self._run(["git", "push", "--quiet"])
        if st["returncode"] != 0:
            return self._error_response("git push --quiet failed", st)

        self.cached_local_ahead = 0
        self.cached_remote_ahead = 0
        self.last_remote_check = datetime.datetime.now()

        return Response(
            json.dumps({"ok": True}),
            200,
            mimetype="application/json",
        )

    @extension_endpoint("status", ["GET"])
    def status(self) -> Response:
        now = datetime.datetime.now()

        if self.last_remote_check is None or (
            (now - self.last_remote_check).total_seconds() > self.remote_check_delay_seconds
        ):
            counts = self._get_ahead_counts()
            if counts["ok"]:
                self.cached_local_ahead = counts["local_ahead"]
                self.cached_remote_ahead = counts["remote_ahead"]
                self.last_remote_check = now
            else:
                return self._error_response("status: failed to get ahead counts", counts)

        dirty = self._is_dirty()

        body = json.dumps({
            "local_ahead": self.cached_local_ahead,
            "remote_ahead": self.cached_remote_ahead,
            "dirty": dirty,
        })
        return Response(body, 200, mimetype="application/json")

    def _is_dirty(self) -> bool:
        st = self._run(["git", "diff", "--no-ext-diff", "--quiet", "--exit-code"])
        if st["returncode"] == 1:
            return True
        # Also check staged/untracked
        st = self._run(["git", "status", "--porcelain"])
        return st["stdout"] != ""

    def _get_ahead_counts(self) -> dict:
        st = self._run(["git", "fetch"])
        if st["returncode"] != 0:
            return self._failure("git fetch failed", st)

        current_branch = self._check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if current_branch["ok"] is False:
            return self._failure("get current branch failed", current_branch)

        remote_branch = self._check_output(
            ["git", "rev-parse", "--abbrev-ref", f"{current_branch['stdout']}@{{upstream}}"]
        )
        if remote_branch["ok"] is False:
            return self._failure("get upstream branch failed", remote_branch)

        # Commits on remote not in local
        remote_ahead = self._check_output(
            ["git", "rev-list", f"HEAD..{remote_branch['stdout']}", "--count"]
        )
        if remote_ahead["ok"] is False:
            return self._failure("git rev-list remote ahead failed", remote_ahead)

        # Commits in local not on remote
        local_ahead = self._check_output(
            ["git", "rev-list", f"{remote_branch['stdout']}..HEAD", "--count"]
        )
        if local_ahead["ok"] is False:
            return self._failure("git rev-list local ahead failed", local_ahead)

        try:
            return {
                "ok": True,
                "local_ahead": int(local_ahead["stdout"]),
                "remote_ahead": int(remote_ahead["stdout"]),
            }
        except ValueError as exc:
            return self._failure(f"failed to parse ahead counts: {exc}", {})

    def _run(self, args: list[str]) -> dict:
        cwd = Path(self.ledger.beancount_file_path).parent
        proc = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
        )
        result = {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "command": " ".join(args),
            "cwd": str(cwd),
        }
        print(f"[FavaGitSync] RUN {result}")
        return result

    def _check_output(self, args: list[str]) -> dict:
        cwd = Path(self.ledger.beancount_file_path).parent
        try:
            proc = subprocess.run(
                args,
                cwd=cwd,
                text=True,
                capture_output=True,
                check=True,
            )
            result = {
                "ok": True,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "returncode": proc.returncode,
                "command": " ".join(args),
                "cwd": str(cwd),
            }
            print(f"[FavaGitSync] CHECK {result}")
            return result
        except subprocess.CalledProcessError as exc:
            result = {
                "ok": False,
                "stdout": (exc.stdout or "").strip(),
                "stderr": (exc.stderr or "").strip(),
                "returncode": exc.returncode,
                "command": " ".join(args),
                "cwd": str(cwd),
            }
            print(f"[FavaGitSync] CHECK FAILED {result}")
            return result
        except Exception as exc:
            result = {
                "ok": False,
                "stdout": "",
                "stderr": str(exc),
                "returncode": -1,
                "command": " ".join(args),
                "cwd": str(cwd),
            }
            print(f"[FavaGitSync] CHECK EXCEPTION {result}")
            return result

    def _failure(self, message: str, data: dict) -> dict:
        merged = {"ok": False, "message": message}
        merged.update(data)
        return merged

    def _error_response(self, message: str, data: dict) -> Response:
        body = (
            f"{message}\n"
            f"command: {data.get('command', '')}\n"
            f"cwd: {data.get('cwd', '')}\n"
            f"returncode: {data.get('returncode', '')}\n"
            f"stdout:\n{data.get('stdout', '')}\n"
            f"stderr:\n{data.get('stderr', '')}\n"
        )
        print(f"[FavaGitSync] ERROR\n{body}")
        return Response(body, 500, mimetype="text/plain")