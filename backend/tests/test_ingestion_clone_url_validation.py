"""Tests for the C-3 SSRF guard on git clone URLs (RepoIngestionEngine).

Covers:
- happy path: github / gitlab / bitbucket / codeberg https URLs accepted
- rejection of: ssh-style (`git@host:repo`), `ssh://` scheme, plain
  `http://`, `file://`, internal hosts (Render metadata, localhost,
  RFC1918), embedded user:pass credentials in netloc, malformed input.

These are pure unit tests — no actual subprocess git clone runs.
The validator is a classmethod, so we call it directly without
instantiating the engine.
"""
from __future__ import annotations

import pytest

from app.refactor.ingestion import RepoIngestionEngine


# ─── allowlisted hosts ────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://github.com/foo/bar.git",
    "https://github.com/foo/bar",
    "https://gitlab.com/foo/bar.git",
    "https://bitbucket.org/foo/bar.git",
    "https://codeberg.org/foo/bar.git",
])
def test_validate_clone_url_accepts_allowlisted_https_hosts(url):
    # Should not raise.
    RepoIngestionEngine._validate_clone_url(url)


# ─── rejection: SSH-style + ssh:// scheme ─────────────────────────────

@pytest.mark.parametrize("url", [
    "git@github.com:victim/private.git",
    "ssh://git@github.com/victim/private.git",
])
def test_rejects_ssh_clone_urls(url):
    with pytest.raises(ValueError, match="SSH-style"):
        RepoIngestionEngine._validate_clone_url(url)


# ─── rejection: plaintext / file / non-https schemes ─────────────────

@pytest.mark.parametrize("url", [
    "http://github.com/foo/bar.git",
    "file:///etc/passwd",
    "ftp://github.com/foo/bar.git",
    "git://github.com/foo/bar.git",
])
def test_rejects_non_https_schemes(url):
    with pytest.raises(ValueError, match="https://"):
        RepoIngestionEngine._validate_clone_url(url)


# ─── rejection: SSRF target hosts ─────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://169.254.169.254/latest/meta-data",  # Render / cloud metadata
    "https://localhost/foo",
    "https://127.0.0.1/foo",
    "https://internal.corp/foo",
    "https://attacker.example/git-smuggle",
])
def test_rejects_non_allowlisted_hosts(url):
    with pytest.raises(ValueError, match="not allowlisted"):
        RepoIngestionEngine._validate_clone_url(url)


# ─── rejection: embedded credentials ─────────────────────────────────

def test_rejects_embedded_credentials():
    with pytest.raises(ValueError, match="Embedded credentials"):
        RepoIngestionEngine._validate_clone_url(
            "https://attacker:token@github.com/foo/bar.git"
        )


# ─── rejection: empty / non-string input ─────────────────────────────

@pytest.mark.parametrize("bad", ["", None, 123, []])
def test_rejects_empty_or_non_string(bad):
    with pytest.raises(ValueError, match="non-empty string"):
        RepoIngestionEngine._validate_clone_url(bad)
