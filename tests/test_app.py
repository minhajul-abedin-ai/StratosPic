import io
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from PIL import Image

from app import analyze_image, app, db
from models import User
from werkzeug.security import generate_password_hash


def setup_function():
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    with app.app_context():
        db.drop_all()
        db.create_all()


def teardown_function():
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/_health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["environment"] == "test"


def test_rule_based_image_analysis():
    image = Image.new("RGB", (1200, 1200), (230, 80, 60))
    tags = analyze_image(image)

    assert "HD" in tags
    assert "Warm tone" in tags


def test_registration_and_login():
    client = app.test_client()

    register = client.post(
        "/register",
        data={
            "username": "minhajtest",
            "password": "StrongPass123",
            "role": "consumer",
        },
        follow_redirects=False,
    )
    assert register.status_code == 302

    login = client.post(
        "/login",
        data={
            "username": "minhajtest",
            "password": "StrongPass123",
            "role": "consumer",
        },
        follow_redirects=False,
    )
    assert login.status_code == 302
    assert "/feed" in login.headers["Location"]


def test_short_password_is_rejected():
    client = app.test_client()

    response = client.post(
        "/register",
        data={
            "username": "shortpass",
            "password": "123",
            "role": "consumer",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"at least 8 characters" in response.data


def test_creator_can_upload_valid_image():
    with app.app_context():
        user = User(
            username="creator",
            role="creator",
            password=generate_password_hash("StrongPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    client.post(
        "/login",
        data={
            "username": "creator",
            "password": "StrongPass123",
            "role": "creator",
        },
    )

    image = Image.new("RGB", (64, 64), (10, 20, 200))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    response = client.post(
        "/upload",
        data={
            "photo": (buffer, "sample.png"),
            "title": "Sample",
            "caption": "Portfolio upload",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302


def test_invalid_upload_is_rejected():
    with app.app_context():
        user = User(
            username="creator2",
            role="creator",
            password=generate_password_hash("StrongPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    client.post(
        "/login",
        data={
            "username": "creator2",
            "password": "StrongPass123",
            "role": "creator",
        },
    )

    response = client.post(
        "/upload",
        data={
            "photo": (io.BytesIO(b"not an image"), "payload.jpg"),
            "title": "Invalid",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"not a valid image" in response.data
