# AGENTS.md

**Generated:** 2026-02-04
**Module:** tests - Test Suite

## OVERVIEW

pytest test suite for GUI, datasources, and database components.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Test fixtures | `conftest.py` | Path setup, common fixtures |
| GUI tests | `test_gui.py` | Flet GUI component tests |
| Datasource tests | `test_datasources.py` | Data source tests |
| Database tests | `test_database.py` | SQLite CRUD tests |
| Crypto tests | `test_crypto_source.py` | Crypto source tests |
| AKShare tests | `test_akshare_sector.py`, `test_akshare_commodity.py` | AKShare-specific tests |

## CONVENTIONS

### Test Structure
- `tests/test_*.py` naming
- Use `pytest` for testing
- Class-based test groups: `class TestClassName:`

### Path Setup
- `conftest.py` sets up sys.path for imports:
  ```python
  PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  sys.path.insert(0, PROJECT_ROOT)
  sys.path.insert(0, SRC_ROOT)
  ```

### Mock Patterns
- Use `unittest.mock` for mocking
- Async tests: `pytest.mark.asyncio` (if async test framework available)
- Mock HTTP responses for data source tests

### Test Naming
- `test_<method_name>` for method tests
- `test_<feature>` for feature tests

## ANTI-PATTERNS

- **Don't hardcode paths**: Use conftest.py path setup
- **Don't skip import setup**: Tests need sys.path configured

## NOTES

- **pytest version**: Specified in requirements.txt (check actual version)
- **Async testing**: If using pytest-asyncio, mark with `@pytest.mark.asyncio`
- **Test data**: May use fixtures for sample fund/commodity data
