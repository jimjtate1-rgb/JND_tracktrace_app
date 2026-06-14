import pytest


@pytest.mark.django_db
def test_container_prefix_redirects(client):
    # MSKU0762594 is a valid ISO 6346 container number for Maersk.
    r = client.get("/ocean/", {"num": "MSKU0762594"})
    assert r.status_code == 302 and "maersk.com" in r["Location"]


@pytest.mark.django_db
def test_bol_scac_redirects(client):
    assert "msc.com" in client.get("/ocean/", {"num": "MEDU123456"})["Location"]
    assert "coscoshipping.com" in client.get("/ocean/", {"num": "COSU12345678"})["Location"]


@pytest.mark.django_db
def test_unknown_prefix_shows_picker(client):
    r = client.get("/ocean/", {"num": "ZZZU1234567"})
    assert r.status_code == 200
    assert b"pick it below" in r.content and b"Supported lines" in r.content


@pytest.mark.django_db
def test_bad_container_check_warns(client):
    # MSKU0762595 has a wrong check digit (should be 4) -> warn rather than redirect.
    r = client.get("/ocean/", {"num": "MSKU0762595"})
    assert r.status_code == 200
    assert b"check digit" in r.content and b"maersk.com" in r.content


@pytest.mark.django_db
def test_manual_pick_redirects(client):
    r = client.get("/ocean/", {"line": "MEDU"})
    assert r.status_code == 302 and "msc.com" in r["Location"]


@pytest.mark.django_db
def test_blank_lists_lines(client):
    r = client.get("/ocean/")
    assert r.status_code == 200 and b"Supported lines" in r.content
