from pathlib import Path
import pytest

from src.utils import create_folder


class TestCreateFolder:
    def test_create_folder_creates_directory(self, tmp_path):
        d = tmp_path / "dist"
        assert not d.exists()

        result = create_folder(d)
        assert isinstance(result, Path)
        assert result.exists() and result.is_dir()

        # idempotent call
        result2 = create_folder(d)
        assert result2 == result

    def test_create_folder_raises_when_file_exists(self, tmp_path):
        f = tmp_path / "dist"
        f.write_text("I am a file")
        assert f.exists() and f.is_file()

        with pytest.raises(RuntimeError):
            create_folder(f)
