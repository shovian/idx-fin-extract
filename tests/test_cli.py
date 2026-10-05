import pytest

from finx.cli import main


def test_test_split_extract_requires_final():
    with pytest.raises(SystemExit) as e:
        main(["extract", "--split", "test"])
    assert "--final" in str(e.value)


def test_inspect_refuses_test_files():
    with pytest.raises(SystemExit) as e:
        main(["inspect", "AMMN/FS AMMN- 31 Dec 2024.pdf", "--page", "4"])
    assert "test split" in str(e.value)
