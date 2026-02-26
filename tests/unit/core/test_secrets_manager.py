"""Tests for the SecretsManager."""

import pytest

from boss.config.secrets_manager import SecretsManager


class TestSecretsManager:
    def test_get_default(self):
        sm = SecretsManager()
        assert sm.get("NONEXISTENT_KEY", "fallback") == "fallback"

    def test_get_empty_default(self):
        sm = SecretsManager()
        assert sm.get("NONEXISTENT_KEY") == ""

    def test_env_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "from_env")
        sm = SecretsManager()
        assert sm.get("MY_SECRET") == "from_env"

    def test_load_from_file(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("API_KEY=abc123\nOTHER=xyz\n")
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        assert sm.get("API_KEY") == "abc123"
        assert sm.get("OTHER") == "xyz"

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("KEY=from_file\n")
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))
        monkeypatch.setenv("KEY", "from_env")

        sm = SecretsManager()
        assert sm.get("KEY") == "from_env"

    def test_comments_and_blanks_ignored(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("# comment\n\nKEY=val\n  # another\n")
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        assert sm.get("KEY") == "val"

    def test_quoted_values_stripped(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text('KEY="quoted_value"\nKEY2=\'single\'\n')
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        assert sm.get("KEY") == "quoted_value"
        assert sm.get("KEY2") == "single"

    def test_thread_safety(self, tmp_path, monkeypatch):
        """Concurrent .get() calls should not crash."""
        import threading

        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("K=V\n")
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        results: list[str] = []

        def reader():
            results.append(sm.get("K", "miss"))

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r == "V" for r in results)

    def test_set_persists_to_file(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        sm.set("NEW_KEY", "new_value")

        assert sm.get("NEW_KEY") == "new_value"
        assert "NEW_KEY=new_value" in secrets_file.read_text(encoding="utf-8")

    def test_delete_removes_key(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("A=1\nB=2\n", encoding="utf-8")
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        deleted = sm.delete("A")

        assert deleted is True
        assert sm.get("A", "") == ""
        content = secrets_file.read_text(encoding="utf-8")
        assert "A=1" not in content
        assert "B=2" in content

    def test_delete_missing_returns_false(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        assert sm.delete("MISSING") is False

    def test_keys_returns_sorted_file_keys(self, tmp_path, monkeypatch):
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("B=2\nA=1\n", encoding="utf-8")
        monkeypatch.setenv("BOSS_SECRETS_FILE", str(secrets_file))

        sm = SecretsManager()
        assert sm.keys() == ["A", "B"]
