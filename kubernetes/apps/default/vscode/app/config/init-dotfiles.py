#!/usr/bin/env python3

import os
import shutil
import subprocess
from pathlib import Path


HOME = Path(os.environ.get("HOME", "/home/coder"))
REPO_URL = os.environ["DOTFILES_REPO_URL"]
VERSION = os.environ.get("DOTFILES_VERSION", "main")
REPO_DIR = HOME / "src/github.com/christfriedbalizou/dotfiles.git"
MISE_BIN = HOME / ".local/bin/mise"
MISE_SHIMS = HOME / ".local/share/mise/shims"


def user_path():
    paths = [
        str(HOME / ".local/bin"),
        str(MISE_SHIMS),
        os.environ.get("PATH", ""),
    ]
    return ":".join(paths)


ENV = os.environ.copy()
ENV["HOME"] = str(HOME)
ENV["PATH"] = user_path()


def run(*args, cwd=None):
    cmd = [str(arg) for arg in args]
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=cwd, env=ENV)


def succeeds(*args):
    cmd = [str(arg) for arg in args]
    result = subprocess.run(
        cmd,
        env=ENV,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def has(command):
    return shutil.which(command, path=ENV["PATH"]) is not None


def sync_repo():
    REPO_DIR.parent.mkdir(parents=True, exist_ok=True)

    run("git", "config", "--global", "--add", "safe.directory", REPO_DIR)

    if (REPO_DIR / ".git").is_dir():
        run("git", "-C", REPO_DIR, "remote", "set-url", "origin", REPO_URL)
        run(
            "git",
            "-C",
            REPO_DIR,
            "fetch",
            "--tags",
            "--force",
            "--prune",
            "origin",
        )
    else:
        if REPO_DIR.exists():
            shutil.rmtree(REPO_DIR)
        run("git", "clone", REPO_URL, REPO_DIR)

    origin_ref = f"origin/{VERSION}"
    origin_commit = f"{origin_ref}^{{commit}}"

    if succeeds("git", "-C", REPO_DIR, "rev-parse", "--verify", origin_commit):
        run(
            "git",
            "-C",
            REPO_DIR,
            "checkout",
            "--force",
            "-B",
            VERSION,
            origin_ref,
        )
        return

    run("git", "-C", REPO_DIR, "checkout", "--force", VERSION)
    run("git", "-C", REPO_DIR, "reset", "--hard", VERSION)


def bootstrap_if_needed():
    if MISE_BIN.exists() or has("mise"):
        return

    run("/bin/bash", REPO_DIR / "bootstrap.sh")


def run_dotfiles_install():
    if has("just"):
        run("just", "install", cwd=REPO_DIR)
        return

    if MISE_BIN.exists():
        run(MISE_BIN, "trust", REPO_DIR, cwd=REPO_DIR)
        run(MISE_BIN, "install", cwd=REPO_DIR)
        run(MISE_BIN, "run", "install", cwd=REPO_DIR)
        return

    print("mise and just are not available; running installer directly")
    ENV["DOTFILES_REPO_ROOT"] = str(REPO_DIR)
    run(REPO_DIR / "scripts/install.sh")


def main():
    sync_repo()
    bootstrap_if_needed()
    run_dotfiles_install()


if __name__ == "__main__":
    main()
