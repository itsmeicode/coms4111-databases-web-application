import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.JSONFileDataService import JSONFileDataService

HARRY_ID = "103cb127-8bb3-4a34-9fd3-c193a9a6cf54"
HERMIONE_ID = "3b3cdd9b-1763-46c0-9731-9c99f7ebfcf9"
RON_ID = "778fc3ef-1fce-4f41-a83e-959de33e77f0"


def _make_service(tmp_path):
    source_file = Path(__file__).resolve().parents[1] / "data" / "harry_potter_data.json"
    working_file = tmp_path / "harry_potter_data.json"
    working_file.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")
    service = JSONFileDataService({"file_path": str(working_file), "primary_key_field": "id"})
    return service


def test_retrieve_by_primary_key(tmp_path):
    service = _make_service(tmp_path)
    row = service.retrieveByPrimaryKey(HARRY_ID)
    assert row["first_name"] == "Harry"


def test_retrieve_by_template(tmp_path):
    service = _make_service(tmp_path)
    rows = service.retrieveByTemplate({"house_name": "Gryffindor"})
    assert len(rows) > 0


def test_create(tmp_path):
    service = _make_service(tmp_path)
    new_uuid = "3f81f429-d89b-4ef2-a63c-67f7fb23ed4f"
    new_id = service.create(
        {
            "id": new_uuid,
            "first_name": "Kingsley",
            "last_name": "Shacklebolt",
            "house_name": "Gryffindor",
        }
    )
    assert new_id == new_uuid


def test_update_by_primary_key(tmp_path):
    service = _make_service(tmp_path)
    updated_count = service.updateByPrimaryKey(HERMIONE_ID, {"house_name": "Ravenclaw"})
    assert updated_count == 1


def test_delete_by_primary_key(tmp_path):
    service = _make_service(tmp_path)
    deleted_count = service.deleteByPrimaryKey(RON_ID)
    assert deleted_count == 1


if __name__ == "__main__":
    test_functions = [
        test_retrieve_by_primary_key,
        test_retrieve_by_template,
        test_create,
        test_update_by_primary_key,
        test_delete_by_primary_key,
    ]

    for test_func in test_functions:
        with tempfile.TemporaryDirectory() as temp_dir:
            test_func(Path(temp_dir))

    print("All manual test calls passed.")
