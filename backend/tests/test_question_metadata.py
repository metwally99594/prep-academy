from services.question_metadata import normalize_question_metadata


def test_nested_country_city_subject_metadata_is_normalized():
    metadata = normalize_question_metadata(
        {
            "country": "Deutschland",
            "city": "Hamburg",
            "year": 2020,
            "subject": {
                "id": "internal",
                "name_de": "Innere Medizin",
                "specialty": {
                    "id": "Kardiologie",
                    "name_de": "Kardiologie",
                },
            },
            "tags": ["exam"],
        }
    )

    assert metadata["country"] == "germany"
    assert metadata["city"] == "hamburg"
    assert metadata["exam_location"] == "hamburg"
    assert metadata["specialty_id"] == "internal"
    assert metadata["subject_id"] == "internal"
    assert metadata["subspecialty_id"] == "cardiology"
    assert metadata["subspecialty_name_de"] == "Kardiologie"
    assert "cardiology" in metadata["tags"]


def test_legacy_flat_metadata_still_works():
    metadata = normalize_question_metadata(
        {
            "specialty_id": "surgery",
            "exam_location": "vienna",
            "country": "AT",
        }
    )

    assert metadata["specialty_id"] == "surgery"
    assert metadata["subject_id"] == "surgery"
    assert metadata["exam_location"] == "vienna"
    assert metadata["country"] == "austria"


def test_switzerland_bern_cardiology_example_metadata():
    metadata = normalize_question_metadata(
        {
            "country": "switzerland",
            "city": "bern",
            "exam_system": "eidgenoessische_pruefung",
            "exam_part": "MC-Pruefung",
            "subject": {
                "id": "internal",
                "name_de": "Innere Medizin",
                "specialty": {"id": "cardiology", "name_de": "Kardiologie"},
            },
        }
    )

    assert metadata["country"] == "switzerland"
    assert metadata["city"] == "bern"
    assert metadata["exam_location"] == "bern"
    assert metadata["specialty_id"] == "internal"
    assert metadata["subspecialty_id"] == "cardiology"
    assert metadata["exam_system"] == "eidgenoessische_pruefung"
    assert metadata["exam_part"] == "mc"
    assert "eidgenoessische_pruefung" in metadata["tags"]
    assert "mc" in metadata["tags"]


def test_city_aliases_cover_at_de_ch():
    cases = {
        ("austria", "Wien"): "vienna",
        ("austria", "Graz"): "graz",
        ("germany", "München"): "munich",
        ("germany", "Köln"): "cologne",
        ("switzerland", "Zürich"): "zurich",
        ("switzerland", "Genf"): "geneva",
    }

    for (country, city), expected_city in cases.items():
        metadata = normalize_question_metadata(
            {"country": country, "city": city, "subject": {"id": "internal"}}
        )
        assert metadata["city"] == expected_city
        assert metadata["exam_location"] == expected_city
