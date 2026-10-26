from pathlib import Path

from glzh.steam import APP_ID, find_app, library_paths

VDF = r'''"libraryfolders"
{
	"0"
	{
		"path"		"/Users/me/Library/Application Support/Steam"
		"apps"		{ "2052040"		"0" }
	}
	"1"
	{
		"path"		"/Volumes/Games\\Steam \"Lib\""
	}
}
'''


def test_library_paths_reads_every_path_and_unescapes():
    assert library_paths(VDF) == [Path("/Users/me/Library/Application Support/Steam"), Path('/Volumes/Games\\Steam "Lib"')]


def test_find_app_searches_secondary_library_using_installdir(tmp_path):
    root, library = tmp_path / "Steam", tmp_path / "Lib"
    (root / "steamapps").mkdir(parents=True)
    (root / "steamapps/libraryfolders.vdf").write_text(f'"libraryfolders" {{ "1" {{ "path" "{library}" }} }}')
    (library / "steamapps").mkdir(parents=True)
    (library / f"steamapps/appmanifest_{APP_ID}.acf").write_text('"AppState" { "installdir" "GL Custom" }')
    app = library / "steamapps/common/GL Custom/goldenlap.app"
    app.mkdir(parents=True)
    assert find_app(root) == app


def test_find_app_returns_none_when_not_installed(tmp_path):
    assert find_app(tmp_path) is None
