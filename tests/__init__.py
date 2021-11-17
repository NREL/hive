from pathlib import Path

def test_dir() -> Path:
    """
    Returns the directory of the tests.
    """
    return Path(__file__).parent