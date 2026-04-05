from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _mock_app():
    app = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = None
    ctx.__exit__.return_value = False
    app.app_context.return_value = ctx
    return app


class TestSeedHardening:
    """Verifies the hardened bootstrap password behavior in seed.py."""

    @patch("seed.User")
    @patch("seed.db.session")
    @patch("seed.secrets.token_urlsafe")
    def test_seed_admin_returns_generated_password_for_new_admin(
        self, mock_token, mock_session, mock_user
    ):
        """Fresh admin creation must return a generated password, not a fixed one."""
        from seed import _seed_admin

        mock_token.return_value = "deterministic-random-password-2026"
        mock_user.query.filter_by.return_value.first.return_value = None

        password = _seed_admin()

        mock_token.assert_called_once_with(16)
        mock_session.add.assert_called_once()
        assert password == "deterministic-random-password-2026"

    @patch("seed.User")
    @patch("seed.db.session")
    @patch("seed.secrets.token_urlsafe")
    def test_seed_admin_returns_none_when_admin_already_exists(
        self, mock_token, mock_session, mock_user
    ):
        """Re-runs must not generate or return a password once admin already exists."""
        from seed import _seed_admin

        mock_user.query.filter_by.return_value.first.return_value = MagicMock()

        password = _seed_admin()

        mock_token.assert_not_called()
        mock_session.add.assert_not_called()
        assert password is None

    @patch("seed.create_app")
    @patch("seed._seed_role_display_names")
    @patch("seed._seed_system_config")
    @patch("seed._seed_categories")
    @patch("seed._seed_uom_catalog")
    @patch("seed._seed_admin")
    @patch("seed.db.session.commit")
    def test_run_seed_prints_password_only_after_successful_commit(
        self,
        mock_commit,
        mock_seed_admin,
        _mock_seed_uom,
        _mock_seed_categories,
        _mock_seed_system_config,
        _mock_seed_role_display_names,
        mock_create_app,
        capsys,
    ):
        """The one-time password must be emitted only after the seed commit succeeds."""
        from seed import run_seed

        mock_create_app.return_value = _mock_app()
        mock_seed_admin.return_value = "deterministic-random-password-2026"

        run_seed()

        mock_commit.assert_called_once_with()
        output = capsys.readouterr().out
        assert "deterministic-random-password-2026" in output
        assert "[seed] admin user created — password: deterministic-random-password-2026" in output

    @patch("seed.create_app")
    @patch("seed._seed_role_display_names")
    @patch("seed._seed_system_config")
    @patch("seed._seed_categories")
    @patch("seed._seed_uom_catalog")
    @patch("seed._seed_admin")
    @patch("seed.db.session.commit", side_effect=RuntimeError("commit failed"))
    def test_run_seed_does_not_print_password_when_commit_fails(
        self,
        _mock_commit,
        mock_seed_admin,
        _mock_seed_uom,
        _mock_seed_categories,
        _mock_seed_system_config,
        _mock_seed_role_display_names,
        mock_create_app,
        capsys,
    ):
        """A failed seed transaction must not leak a password for an uncommitted admin row."""
        from seed import run_seed

        mock_create_app.return_value = _mock_app()
        mock_seed_admin.return_value = "deterministic-random-password-2026"

        with pytest.raises(RuntimeError, match="commit failed"):
            run_seed()

        output = capsys.readouterr().out
        assert "Running seed..." in output
        assert "deterministic-random-password-2026" not in output

    def test_seed_script_no_longer_contains_admin123_literal(self):
        """seed.py must no longer contain the legacy fixed bootstrap password."""
        seed_path = Path(__file__).resolve().parents[1] / "seed.py"
        content = seed_path.read_text()

        assert "admin123" not in content

    def test_readme_no_longer_claims_setup_creates_the_first_admin(self):
        """README must describe setup/admin bootstrap flow accurately after hardening."""
        readme_path = Path(__file__).resolve().parents[2] / "README.md"
        content = readme_path.read_text()

        assert (
            "create the initial admin account through the authenticated first-run setup flow"
            not in content
        )
        assert "does **not** create the first admin account" in content
