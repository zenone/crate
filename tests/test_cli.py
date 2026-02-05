"""
Tests for the CLI interface.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

from crate.cli.main import main, parse_args


@pytest.fixture
def mock_api():
    # Patch the RenamerAPI class inside the module object via sys.modules
    # This avoids confusion between the module 'main' and function 'main'
    with patch.object(sys.modules["crate.cli.main"], "RenamerAPI") as mock:
        yield mock

def test_parse_args():
    """Test argument parsing."""
    # --recursive is now default, test --no-recursive
    args = parse_args(["/tmp/test", "--dry-run", "--no-recursive", "-v", "--analyze"])
    assert str(args.path) == "/tmp/test"
    assert args.dry_run is True
    assert args.recursive is False
    assert args.verbosity == 1
    assert args.analyze is True

def test_main_success(mock_api, tmp_path):
    """Test successful execution."""
    # Setup mock return
    instance = mock_api.return_value
    instance.rename_files.return_value = MagicMock(
        total=10, renamed=5, skipped=5, errors=0
    )

    # Run main with default args (recursive=True, analyze=False)
    exit_code = main([str(tmp_path), "--dry-run"])

    # Verify API called correctly
    assert exit_code == 0
    mock_api.assert_called_once()
    instance.rename_files.assert_called_once()

    # Verify request args
    call_args = instance.rename_files.call_args[0][0]
    assert call_args.path == tmp_path
    assert call_args.dry_run is True
    assert call_args.recursive is True
    assert call_args.auto_detect is False

def test_main_no_files(mock_api, tmp_path):
    """Test execution finding no files."""
    instance = mock_api.return_value
    instance.rename_files.return_value = MagicMock(
        total=0, renamed=0, skipped=0, errors=0
    )

    exit_code = main([str(tmp_path)])

    # Should exit with error code 1 (or warning)
    assert exit_code == 1

def test_main_with_errors(mock_api, tmp_path):
    """Test execution with errors."""
    instance = mock_api.return_value
    instance.rename_files.return_value = MagicMock(
        total=10, renamed=5, skipped=0, errors=5
    )

    exit_code = main([str(tmp_path)])

    # Should exit with error code 1
    assert exit_code == 1
