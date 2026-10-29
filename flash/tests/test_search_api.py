from __future__ import annotations

import io
import zipfile

from conftest import selfie_bytes

DEV = "d" * 20


def search(client, who, slug="jebs-2026", device=DEV, consent=True, headers=None, extra=None):
    return client.post(
        f"/v1/public/events/{slug}/search",
        files=[("selfie", ("s.jpg", selfie_bytes(who, extra), "image/jpeg"))],
        data={"consent": "true" if consent else "false"},
        headers={"X-Device-Id": device, **(headers or {})},
    )


def names(client, token, tier="certain"):
    r = client.get(f"/v1/public/galleries/{token}", params={"tier": tier})
    assert r.status_code == 200, r.text
    return sorted(i["name"] for i in r.json()["items"]), r.json()


def test_public_listing(client, indexed_event):
    assert client.get("/v1/public/tenant").json()["name"] == "CBDE"
    evs = client.get("/v1/public/events").json()
    assert [e["slug"] for e in evs] == ["jebs-2026"]
    assert evs[0]["photos"] == 4 and evs[0]["requires_code"] is False


def test_selfie_finds_all_photos_of_the_person(client, indexed_event):
    r = search(client, "ana")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["counts"] == {"certain": 2, "maybe": 0}
    assert "sim" not in r.text  # similaridade bruta não vai ao cliente
    got, g = names(client, body["gallery_token"])
    assert got == ["a1.jpg", "a2.jpg"]
    assert g["items"][0]["facets"]["dia"] == "Sabado"

    r = search(client, "bia", device="e" * 20)
    assert names(client, r.json()["gallery_token"])[0] == ["a1.jpg", "b1.jpg"]


def test_person_without_photos_gets_empty_result(client, indexed_event):
    r = search(client, "edu")
    assert r.status_code == 200
    assert r.json()["counts"] == {"certain": 0, "maybe": 0}


def test_selfie_validation_messages(client, indexed_event):
    from PIL import Image

    blank = io.BytesIO()
    Image.new("RGB", (600, 600), (128, 128, 128)).save(blank, "JPEG")
    r = client.post(
        "/v1/public/events/jebs-2026/search",
        files=[("selfie", ("s.jpg", blank.getvalue(), "image/jpeg"))],
        data={"consent": "true"},
        headers={"X-Device-Id": DEV},
    )
    assert r.status_code == 422 and r.json()["detail"]["reason"] == "no_face"

    r = search(client, "ana", extra="bia")  # duas pessoas na selfie
    assert r.status_code == 422 and r.json()["detail"]["reason"] == "multiple_faces"

    r = client.post(
        "/v1/public/events/jebs-2026/search",
        files=[("selfie", ("s.jpg", b"nao sou imagem", "image/jpeg"))],
        data={"consent": "true"},
        headers={"X-Device-Id": DEV},
    )
    assert r.status_code == 422 and r.json()["detail"]["reason"] == "invalid_image"


def test_requires_consent_and_device(client, indexed_event):
    assert search(client, "ana", consent=False).status_code == 400
    assert search(client, "ana", device="curto").status_code == 400


def test_selfie_is_never_persisted(client, indexed_event, env):
    def snapshot():
        return sorted(
            str(p.relative_to(env))
            for p in env.rglob("*")
            if p.is_file() and not p.name.startswith("test.db")
        )

    before = snapshot()
    assert search(client, "ana").status_code == 200
    assert snapshot() == before  # nenhum arquivo novo em lugar nenhum


def test_event_code_protects_search(client, admin, indexed_event):
    client.patch(f"/v1/admin/events/{indexed_event}", headers=admin, json={"access_code": "JEBS26"})
    assert client.get("/v1/public/events").json()[0]["requires_code"] is True
    assert search(client, "ana").status_code == 401

    assert (
        client.post("/v1/public/events/jebs-2026/access", json={"code": "errado"}).status_code
        == 403
    )
    token = client.post("/v1/public/events/jebs-2026/access", json={"code": "jebs26"}).json()[
        "token"
    ]
    r = search(client, "ana", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["counts"]["certain"] == 2


def test_event_code_bruteforce_is_limited(client, admin, indexed_event):
    client.patch(f"/v1/admin/events/{indexed_event}", headers=admin, json={"access_code": "JEBS26"})
    codes = [
        client.post("/v1/public/events/jebs-2026/access", json={"code": f"x{i}"}).status_code
        for i in range(10)
    ]
    assert codes[:8] == [403] * 8 and codes[8] == 429


def test_daily_limit_in_minors_mode(client, indexed_event, monkeypatch):
    monkeypatch.setenv("FLASH_SEARCHES_PER_DAY", "2")
    from flash.config import get_settings

    get_settings.cache_clear()
    assert [search(client, "ana").status_code for _ in range(3)] == [200, 200, 429]
    assert search(client, "ana", device="o" * 20).status_code == 200  # outro dispositivo


def test_download_original_zip_and_thumbs(client, indexed_event, photos_dir):
    token = search(client, "ana").json()["gallery_token"]
    items = client.get(f"/v1/public/galleries/{token}").json()["items"]
    first = items[0]
    assert client.get(first["thumb"]).headers["content-type"] == "image/jpeg"
    assert client.get(first["preview"]).status_code == 200
    orig = client.get(first["original"])
    assert orig.status_code == 200
    assert orig.content == (photos_dir / "Sabado" / "Volei" / first["name"]).read_bytes()
    assert "attachment" in orig.headers["content-disposition"]

    z = client.get(f"/v1/public/galleries/{token}/zip")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
        assert zf.testzip() is None
        assert sorted(zf.namelist()) == ["a1.jpg", "a2.jpg"]
        assert zf.read("a2.jpg") == (photos_dir / "Sabado" / "Volei" / "a2.jpg").read_bytes()

    sel = client.get(f"/v1/public/galleries/{token}/zip", params={"ids": first["id"]})
    with zipfile.ZipFile(io.BytesIO(sel.content)) as zf:
        assert zf.namelist() == [first["name"]]


def test_gallery_is_scoped_to_search_and_tokens_are_checked(client, indexed_event):
    t_ana = search(client, "ana").json()["gallery_token"]
    t_caio = search(client, "caio", device="c" * 20).json()["gallery_token"]
    caio_photo = client.get(f"/v1/public/galleries/{t_caio}").json()["items"][0]
    # foto do Caio NÃO abre com o token da Ana, mesmo sabendo o id
    url = f"/v1/public/galleries/{t_ana}/photos/{caio_photo['id']}/original"
    assert client.get(url).status_code == 404
    assert client.get("/v1/public/galleries/token-falso").status_code == 401


def test_remove_request_hides_photo_immediately(client, admin, indexed_event):
    token = search(client, "ana").json()["gallery_token"]
    pid = client.get(f"/v1/public/galleries/{token}").json()["items"][0]["id"]
    r = client.post(f"/v1/public/galleries/{token}/photos/{pid}/feedback", json={"kind": "remove"})
    assert r.status_code == 200
    assert len(client.get(f"/v1/public/galleries/{token}").json()["items"]) == 1
    # e some de buscas novas
    t2 = search(client, "ana", device="n" * 20).json()["gallery_token"]
    assert len(client.get(f"/v1/public/galleries/{t2}").json()["items"]) == 1
    assert client.get("/v1/admin/feedback", headers=admin).json()[0]["kind"] == "remove"


def test_admin_hide_and_show(client, admin, indexed_event):
    photos = client.get(f"/v1/admin/events/{indexed_event}/photos", headers=admin).json()
    a1 = next(p for p in photos if p["name"] == "a1.jpg")
    client.post(f"/v1/admin/photos/{a1['id']}/hide", headers=admin)
    t = search(client, "ana").json()["gallery_token"]
    assert names(client, t)[0] == ["a2.jpg"]
    client.post(f"/v1/admin/photos/{a1['id']}/show", headers=admin)
    t = search(client, "ana", device="z" * 20).json()["gallery_token"]
    assert names(client, t)[0] == ["a1.jpg", "a2.jpg"]


def test_admin_requires_token(client, indexed_event):
    assert client.get("/v1/admin/events").status_code == 401
    assert (
        client.get("/v1/admin/events", headers={"Authorization": "Bearer errado"}).status_code
        == 401
    )


def test_metrics(client, admin, indexed_event):
    search(client, "ana")
    search(client, "edu", device="m" * 20)
    m = client.get(f"/v1/admin/events/{indexed_event}/metrics", headers=admin).json()
    assert m["searches"] == 2 and m["with_results"] == 1 and m["success_rate"] == 0.5


def test_tenant_isolation(client, admin, indexed_event):
    client.post("/v1/admin/tenants", headers=admin, json={"slug": "outra", "name": "Outra Liga"})
    h = {"X-Flash-Tenant": "outra"}
    assert client.get("/v1/public/events", headers=h).json() == []
    assert client.get("/v1/public/events/jebs-2026", headers=h).status_code == 404
    r = client.post(
        "/v1/public/events/jebs-2026/search",
        files=[("selfie", ("s.jpg", selfie_bytes("ana"), "image/jpeg"))],
        data={"consent": "true"},
        headers={"X-Device-Id": DEV, **h},
    )
    assert r.status_code == 404


def test_closed_event_is_not_public(client, admin, indexed_event):
    client.patch(f"/v1/admin/events/{indexed_event}", headers=admin, json={"status": "closed"})
    assert client.get("/v1/public/events").json() == []
    assert search(client, "ana").status_code == 404
