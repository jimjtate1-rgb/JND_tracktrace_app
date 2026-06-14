import pytest


@pytest.mark.django_db
def test_known_prefix_redirects_to_airline(client):
    r = client.get("/aircargo/", {"awb": "160-12345675"})
    assert r.status_code == 302 and "cathaycargo.com" in r["Location"]


@pytest.mark.django_db
def test_china_prefixes(client):
    assert "airchinacargo.com" in client.get("/aircargo/", {"awb": "999-12345675"})["Location"]
    assert "csair.com" in client.get("/aircargo/", {"awb": "784-12345675"})["Location"]


@pytest.mark.django_db
def test_unknown_prefix_shows_picker(client):
    r = client.get("/aircargo/", {"awb": "555-12345678"})
    assert r.status_code == 200
    assert b"pick it below" in r.content
    assert b"Supported airlines" in r.content


@pytest.mark.django_db
def test_bad_check_digit_warns_but_offers_link(client):
    # 160 is Cathay, but a wrong check digit should warn rather than silently redirect.
    r = client.get("/aircargo/", {"awb": "160-12345678"})
    assert r.status_code == 200
    assert b"check digit" in r.content and b"cathaycargo.com" in r.content


@pytest.mark.django_db
def test_blank_lists_airlines(client):
    r = client.get("/aircargo/")
    assert r.status_code == 200 and b"Supported airlines" in r.content


@pytest.mark.django_db
def test_manual_airline_pick_redirects(client):
    r = client.get("/aircargo/", {"airline": "EK"})
    assert r.status_code == 302 and "skycargo.com" in r["Location"]
