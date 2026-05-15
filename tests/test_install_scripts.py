# pattern: Imperative Shell
"""Structural tests for install/ scripts.

These tests verify file existence, permissions, line endings, syntax
validity, and required content sentinels. They do not execute the scripts
(that would require a running Docker environment).
"""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
INSTALL_DIR = REPO_ROOT / "install"

START_SH = INSTALL_DIR / "start.sh"
START_PS1 = INSTALL_DIR / "start.ps1"
README = INSTALL_DIR / "README.md"

SETUP_SH = INSTALL_DIR / "setup.sh"
SETUP_PS1 = INSTALL_DIR / "setup.ps1"


class TestStartScriptsExist:
    def test_install_directory_exists(self):
        assert INSTALL_DIR.is_dir(), f"install/ directory not found at {INSTALL_DIR}"

    def test_start_sh_exists(self):
        assert START_SH.exists(), f"install/start.sh not found at {START_SH}"

    def test_start_ps1_exists(self):
        assert START_PS1.exists(), f"install/start.ps1 not found at {START_PS1}"

    def test_readme_exists(self):
        assert README.exists(), f"install/README.md not found at {README}"


class TestStartShExecutable:
    """AC4.3 — start.sh has executable bit and LF line endings."""

    def test_start_sh_executable_bit(self):
        # On Windows, NTFS does not support Unix executable bits in the filesystem.
        # Check git index instead, which properly stores the 100755 mode.
        if sys.platform == "win32":
            # Windows: verify via git index
            result = subprocess.run(
                ["git", "ls-files", "--stage", "install/start.sh"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, "git ls-files failed"
            # Mode is first space-separated field: "100755 ..."
            mode_str = result.stdout.split()[0]
            assert mode_str == "100755", (
                f"install/start.sh git mode should be 100755, got {mode_str}"
            )
        else:
            # Unix: verify filesystem executable bit
            mode = os.stat(START_SH).st_mode
            assert mode & stat.S_IXUSR, "install/start.sh missing executable bit (S_IXUSR)"

    def test_start_sh_lf_line_endings(self):
        content = START_SH.read_bytes()
        assert b"\r\n" not in content, (
            "install/start.sh contains CRLF line endings — must use LF only"
        )


class TestStartShSyntax:
    """AC4.1 — start.sh passes bash -n syntax check."""

    def test_start_sh_bash_syntax(self):
        bash = shutil.which("bash")
        if bash is None:
            pytest.skip("bash not available on this system")
        result = subprocess.run(
            [bash, "-n", str(START_SH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n install/start.sh failed:\n{result.stderr}"
        )


class TestStartPs1Syntax:
    """AC4.2 — start.ps1 passes pwsh syntax check."""

    def test_start_ps1_pwsh_syntax(self):
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            pytest.skip("pwsh not available on this system")
        check_script = (
            "$errors = $null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{START_PS1}', [ref]$null, [ref]$errors); "
            "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
        )
        result = subprocess.run(
            [pwsh, "-NonInteractive", "-Command", check_script],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"pwsh syntax check failed for install/start.ps1:\n{result.stderr}"
        )


class TestStartShSentinels:
    """Structural content checks for start.sh (AC3 pattern verification)."""

    def setup_method(self):
        self.content = START_SH.read_text(encoding="utf-8")

    def test_health_url_present(self):
        assert "http://localhost:8000/health" in self.content, (
            "start.sh missing health URL sentinel (http://localhost:8000/health)"
        )

    def test_app_url_present(self):
        assert "http://localhost:3000" in self.content, (
            "start.sh missing app URL sentinel (http://localhost:3000)"
        )

    def test_health_loop_present(self):
        assert "HEALTH_TIMEOUT" in self.content, (
            "start.sh missing HEALTH_TIMEOUT variable (health check loop pattern)"
        )

    def test_env_missing_message(self):
        # AC3.3 — .env missing → exit 1 "run setup first"
        assert "setup" in self.content.lower(), (
            "start.sh missing 'setup' reference for AC3.3 (.env missing message)"
        )

    def test_docker_not_running_exit(self):
        # AC3.4 — Docker not running → exit 1
        assert "docker info" in self.content, (
            "start.sh missing 'docker info' check for AC3.4"
        )

    def test_health_timeout_logs_exit(self):
        # AC3.5 — health timeout → print logs tail → exit 1
        assert "docker compose logs" in self.content, (
            "start.sh missing 'docker compose logs' for AC3.5"
        )

    def test_docker_compose_up(self):
        # AC3.1 — not running → docker compose up -d
        assert "docker compose up -d" in self.content, (
            "start.sh missing 'docker compose up -d' for AC3.1"
        )

    def test_already_running_check(self):
        # AC3.2 — already running → skip up -d
        assert "docker compose ps" in self.content, (
            "start.sh missing 'docker compose ps' check for AC3.2"
        )


class TestStartPs1Sentinels:
    """Structural content checks for start.ps1 (AC3 pattern verification)."""

    def setup_method(self):
        self.content = START_PS1.read_text(encoding="utf-8")

    def test_health_url_present(self):
        assert "http://localhost:8000/health" in self.content, (
            "start.ps1 missing health URL sentinel"
        )

    def test_app_url_present(self):
        assert "http://localhost:3000" in self.content, (
            "start.ps1 missing app URL sentinel"
        )

    def test_health_loop_present(self):
        assert "healthTimeout" in self.content, (
            "start.ps1 missing healthTimeout variable (health check loop pattern)"
        )

    def test_env_missing_message(self):
        # AC3.3
        assert "setup" in self.content.lower(), (
            "start.ps1 missing 'setup' reference for AC3.3"
        )

    def test_docker_not_running_exit(self):
        # AC3.4
        assert "docker info" in self.content, (
            "start.ps1 missing 'docker info' check for AC3.4"
        )

    def test_health_timeout_logs_exit(self):
        # AC3.5
        assert "docker compose logs" in self.content, (
            "start.ps1 missing 'docker compose logs' for AC3.5"
        )

    def test_docker_compose_up(self):
        # AC3.1
        assert "docker compose up -d" in self.content, (
            "start.ps1 missing 'docker compose up -d' for AC3.1"
        )

    def test_already_running_check(self):
        # AC3.2
        assert "docker compose ps" in self.content, (
            "start.ps1 missing 'docker compose ps' check for AC3.2"
        )


class TestReadmeSentinels:
    """AC4.4 — README.md covers both Windows and Linux quickstart paths."""

    def setup_method(self):
        self.content = README.read_text(encoding="utf-8")

    def test_windows_section_present(self):
        assert "Windows" in self.content, (
            "install/README.md missing Windows section (AC4.4)"
        )

    def test_linux_section_present(self):
        assert "Linux" in self.content, (
            "install/README.md missing Linux section (AC4.4)"
        )

    def test_setup_reference_present(self):
        assert "setup" in self.content.lower(), (
            "install/README.md missing reference to setup script"
        )

    def test_start_reference_present(self):
        assert "start" in self.content.lower(), (
            "install/README.md missing reference to start script"
        )


class TestSetupScriptsExist:
    def test_setup_sh_exists(self):
        assert SETUP_SH.exists(), f"install/setup.sh not found at {SETUP_SH}"

    def test_setup_ps1_exists(self):
        assert SETUP_PS1.exists(), f"install/setup.ps1 not found at {SETUP_PS1}"


class TestSetupShExecutable:
    """AC4.3 — setup.sh has executable bit and LF line endings."""

    def test_setup_sh_executable_bit(self):
        # On Windows, NTFS does not support Unix executable bits in the filesystem.
        # Check git index instead, which properly stores the 100755 mode.
        if sys.platform == "win32":
            # Windows: verify via git index
            result = subprocess.run(
                ["git", "ls-files", "--stage", "install/setup.sh"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, "git ls-files failed"
            # Mode is first space-separated field: "100755 ..."
            mode_str = result.stdout.split()[0]
            assert mode_str == "100755", (
                f"install/setup.sh git mode should be 100755, got {mode_str}"
            )
        else:
            # Unix: verify filesystem executable bit
            mode = os.stat(SETUP_SH).st_mode
            assert mode & stat.S_IXUSR, "install/setup.sh missing executable bit (S_IXUSR)"

    def test_setup_sh_lf_line_endings(self):
        content = SETUP_SH.read_bytes()
        assert b"\r\n" not in content, (
            "install/setup.sh contains CRLF line endings — must use LF only"
        )


class TestSetupShSyntax:
    """AC4.1 — setup.sh passes bash -n syntax check."""

    def test_setup_sh_bash_syntax(self):
        bash = shutil.which("bash")
        if bash is None:
            pytest.skip("bash not available on this system")
        result = subprocess.run(
            [bash, "-n", str(SETUP_SH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n install/setup.sh failed:\n{result.stderr}"
        )


class TestSetupPs1Syntax:
    """AC4.2 — setup.ps1 passes pwsh syntax check."""

    def test_setup_ps1_pwsh_syntax(self):
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            pytest.skip("pwsh not available on this system")
        check_script = (
            "$errors = $null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{SETUP_PS1}', [ref]$null, [ref]$errors); "
            "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
        )
        result = subprocess.run(
            [pwsh, "-NonInteractive", "-Command", check_script],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"pwsh syntax check failed for install/setup.ps1:\n{result.stderr}"
        )


class TestSetupShSentinels:
    """Structural content checks for setup.sh (AC1, AC2 pattern verification)."""

    def setup_method(self):
        self.content = SETUP_SH.read_text(encoding="utf-8")

    def test_google_api_key_substitution(self):
        # AC1.1 — produces correct .env
        assert "GOOGLE_API_KEY" in self.content, (
            "setup.sh missing GOOGLE_API_KEY substitution (AC1.1)"
        )

    def test_change_me_substitution(self):
        # AC1.1 — no CHANGE_ME sentinel remaining after setup
        assert "CHANGE_ME" in self.content, (
            "setup.sh must reference CHANGE_ME to substitute it out (AC1.1)"
        )

    def test_password_confirm_loop(self):
        # AC1.2 — password confirmation loop re-prompts on mismatch
        assert "admin_password_confirm" in self.content, (
            "setup.sh missing password confirmation variable (AC1.2)"
        )

    def test_password_min_length_check(self):
        # AC1.3 — passwords shorter than 8 chars rejected
        assert "8" in self.content, (
            "setup.sh missing minimum password length check (AC1.3)"
        )

    def test_docker_not_running_exit(self):
        # AC1.4 — Docker not running → exit non-zero
        assert "docker info" in self.content, (
            "setup.sh missing docker info check (AC1.4)"
        )

    def test_overwrite_guard_present(self):
        # AC1.5 — existing files → warn + prompt (default No)
        assert "already exists" in self.content or "overwrite" in self.content.lower(), (
            "setup.sh missing overwrite guard for existing config files (AC1.5)"
        )

    def test_docker_compose_build(self):
        # AC2.1 — docker compose build runs after config writes
        assert "docker compose build" in self.content, (
            "setup.sh missing 'docker compose build' (AC2.1)"
        )

    def test_docker_compose_up(self):
        # AC2.1 — docker compose up -d runs
        assert "docker compose up -d" in self.content, (
            "setup.sh missing 'docker compose up -d' (AC2.1)"
        )

    def test_health_url_present(self):
        # AC2.2 — health check at localhost:8000/health
        assert "http://localhost:8000/health" in self.content, (
            "setup.sh missing health check URL (AC2.2)"
        )

    def test_health_timeout_logs(self):
        # AC2.2 — logs tail on timeout
        assert "docker compose logs" in self.content, (
            "setup.sh missing 'docker compose logs' on health timeout (AC2.2)"
        )

    def test_chown_step_linux(self):
        # Linux chown step (no wsl.exe involved for setup.sh)
        assert "chown" in self.content, (
            "setup.sh missing chown step for data/ directory"
        )

    def test_app_url_present(self):
        assert "http://localhost:3000" in self.content, (
            "setup.sh missing app URL (http://localhost:3000)"
        )


class TestSetupPs1Sentinels:
    """Structural content checks for setup.ps1 (AC1, AC2, AC2.3 pattern verification)."""

    def setup_method(self):
        self.content = SETUP_PS1.read_text(encoding="utf-8")

    def test_google_api_key_substitution(self):
        # AC1.1
        assert "GOOGLE_API_KEY" in self.content, (
            "setup.ps1 missing GOOGLE_API_KEY substitution (AC1.1)"
        )

    def test_change_me_substitution(self):
        # AC1.1
        assert "CHANGE_ME" in self.content, (
            "setup.ps1 must reference CHANGE_ME to substitute it out (AC1.1)"
        )

    def test_password_confirm_loop(self):
        # AC1.2
        assert "pw2" in self.content or "confirm" in self.content.lower(), (
            "setup.ps1 missing password confirmation (AC1.2)"
        )

    def test_password_min_length_check(self):
        # AC1.3
        assert ".Length -lt 8" in self.content or "Length -lt 8" in self.content, (
            "setup.ps1 missing minimum password length check (AC1.3)"
        )

    def test_docker_not_running_exit(self):
        # AC1.4
        assert "docker info" in self.content, (
            "setup.ps1 missing docker info check (AC1.4)"
        )

    def test_overwrite_guard_present(self):
        # AC1.5
        assert "already exists" in self.content or "overwrite" in self.content.lower(), (
            "setup.ps1 missing overwrite guard (AC1.5)"
        )

    def test_docker_compose_build(self):
        # AC2.1
        assert "docker compose build" in self.content, (
            "setup.ps1 missing 'docker compose build' (AC2.1)"
        )

    def test_docker_compose_up(self):
        # AC2.1
        assert "docker compose up -d" in self.content, (
            "setup.ps1 missing 'docker compose up -d' (AC2.1)"
        )

    def test_health_url_present(self):
        # AC2.2
        assert "http://localhost:8000/health" in self.content, (
            "setup.ps1 missing health check URL (AC2.2)"
        )

    def test_health_timeout_logs(self):
        # AC2.2
        assert "docker compose logs" in self.content, (
            "setup.ps1 missing 'docker compose logs' on health timeout (AC2.2)"
        )

    def test_data_dir_created(self):
        # AC2.3 — data/ directory created before docker compose build (Windows: New-Item, not wsl chown)
        assert "data" in self.content, (
            "setup.ps1 missing data/ directory creation step (AC2.3)"
        )

    def test_app_url_present(self):
        assert "http://localhost:3000" in self.content, (
            "setup.ps1 missing app URL (AC2.1)"
        )

    def test_secure_string_input(self):
        # Masked input — AsSecureString
        assert "AsSecureString" in self.content, (
            "setup.ps1 missing Read-Host -AsSecureString for masked input"
        )
