from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_does_not_swallow_backend_test_failures():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest tests -xvs --tb=short" in ci
    assert not any("pytest " in line and "||" in line for line in ci.splitlines())
    assert "npm test" in ci


def test_local_databases_and_env_variants_excluded_from_image():
    rules = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for pattern in (".env", ".env.*", "*.db", "*.sqlite", "*.sqlite3", "*.pem", "*.key"):
        assert pattern in rules
