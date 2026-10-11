import io
import logging
import os
import secrets
import urllib.parse
from datetime import datetime
from uuid import uuid4

from azure.storage.blob import BlobServiceClient
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from PIL import Image, ImageStat, UnidentifiedImageError
from textblob import TextBlob
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from models import Comment, Like, Photo, Save, User, db

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("stratospic")

APP_ENV = os.getenv("APP_ENV", "development").lower()
PRODUCTION = APP_ENV == "production"

app = Flask(__name__)

secret_key = os.getenv("SECRET_KEY")
if PRODUCTION and not secret_key:
    raise RuntimeError("SECRET_KEY must be configured when APP_ENV=production.")
app.config["SECRET_KEY"] = secret_key or secrets.token_hex(32)

app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024))
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = PRODUCTION
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = PRODUCTION

csrf = CSRFProtect(app)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
Image.MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "25000000"))


def _mask_db_uri(uri: str) -> str:
    try:
        if uri.startswith("sqlite"):
            return uri
        scheme, rest = uri.split("://", 1)
        if "@" not in rest:
            return uri
        userinfo, hostpath = rest.split("@", 1)
        user = userinfo.split(":", 1)[0]
        return f"{scheme}://{user}:****@{hostpath}"
    except Exception:
        return "****"


def _database_uri() -> str:
    raw_conn = os.getenv("AZURE_POSTGRESQL_CONNECTIONSTRING") or os.getenv(
        "DATABASE_URL"
    )
    if not raw_conn:
        os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
        uri = f"sqlite:///{os.path.join(app.root_path, 'instance', 'app.db')}"
        logger.warning(
            "No PostgreSQL connection configured; using local SQLite development storage."
        )
        return uri

    if "://" in raw_conn:
        return raw_conn

    try:
        conn_params = dict(pair.split("=", 1) for pair in raw_conn.split())
        user = conn_params.get("user") or conn_params.get("username")
        password = urllib.parse.quote_plus(conn_params.get("password", ""))
        host = conn_params.get("host", "localhost")
        port = conn_params.get("port", "5432")
        dbname = conn_params.get("dbname") or conn_params.get("database")
        if not user or not dbname:
            raise ValueError("Azure PostgreSQL connection string is incomplete")
        return (
            f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
            "?sslmode=require"
        )
    except Exception as exc:
        raise RuntimeError("Could not parse database connection string") from exc


app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
logger.info("Database configured: %s", _mask_db_uri(app.config["SQLALCHEMY_DATABASE_URI"]))

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "photos")
LOCAL_UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(LOCAL_UPLOAD_FOLDER, exist_ok=True)

blob_service_client = None
if AZURE_CONNECTION_STRING:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_CONNECTION_STRING
        )
        logger.info("Azure Blob Storage client initialized.")
    except Exception:
        logger.exception("Azure Blob Storage initialization failed.")

db.init_app(app)
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def _has_allowed_extension(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def _validated_image(upload):
    if not upload or not upload.filename:
        raise ValueError("No image was provided.")

    filename = secure_filename(upload.filename)
    if not filename or not _has_allowed_extension(filename):
        raise ValueError("Only JPG, JPEG, PNG and WEBP images are supported.")

    try:
        raw = upload.read()
        if not raw:
            raise ValueError("The uploaded image is empty.")

        probe = Image.open(io.BytesIO(raw))
        probe.verify()

        image = Image.open(io.BytesIO(raw))
        image.load()
        if image.width * image.height > Image.MAX_IMAGE_PIXELS:
            raise ValueError("The uploaded image is too large.")

        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc


def _store_image(image: Image.Image, prefix: str) -> str:
    image = image.copy()
    image.thumbnail((1080, 1080))

    blob_name = f"{prefix}_{uuid4().hex}.jpg"
    output = io.BytesIO()
    image.save(output, format="JPEG", optimize=True, quality=85)
    output.seek(0)

    if blob_service_client and AZURE_CONTAINER_NAME:
        client = blob_service_client.get_blob_client(
            container=AZURE_CONTAINER_NAME,
            blob=blob_name,
        )
        client.upload_blob(output, overwrite=False)
        return client.url

    local_path = os.path.join(LOCAL_UPLOAD_FOLDER, blob_name)
    with open(local_path, "wb") as handle:
        handle.write(output.getvalue())
    return url_for("static", filename=f"uploads/{blob_name}", _external=True)


def analyze_image(image: Image.Image) -> str:
    """Return deterministic image metadata tags; this is rule-based, not ML."""
    if image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size
    tags = ["HD" if width * height > 1_000_000 else "SD"]

    brightness = ImageStat.Stat(image.convert("L")).mean[0]
    if brightness > 150:
        tags.append("Bright")
    elif brightness < 80:
        tags.append("Dark")
    else:
        tags.append("Neutral lighting")

    red, green, blue = image.resize((1, 1)).getpixel((0, 0))
    if red > green and red > blue:
        tags.append("Warm tone")
    elif blue > red and blue > green:
        tags.append("Cool tone")
    else:
        tags.append("Balanced colour")

    return " | ".join(tags)


@app.template_filter("timeago")
def timeago(date):
    if not date:
        return "Recently"
    seconds = (datetime.utcnow() - date).total_seconds()
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


@app.errorhandler(413)
def upload_too_large(_error):
    return "Upload too large", 413


@app.route("/")
def home():
    return (
        redirect(url_for("feed"))
        if current_user.is_authenticated
        else redirect(url_for("login"))
    )


@app.route("/feed")
@login_required
def feed():
    query = (request.args.get("q") or "").strip()
    photos_query = Photo.query.join(User)
    if query:
        search_term = f"%{query}%"
        photos_query = photos_query.filter(
            (Photo.title.ilike(search_term))
            | (Photo.caption.ilike(search_term))
            | (Photo.location.ilike(search_term))
            | (User.username.ilike(search_term))
        )
    photos = photos_query.order_by(Photo.uploaded_at.desc()).all()
    return render_template("feed.html", photos=photos)


@app.route("/u/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    photos = Photo.query.filter_by(user_id=user.id).order_by(Photo.uploaded_at.desc()).all()
    saved = Photo.query.join(Save).filter(Save.user_id == user.id).all()
    liked = Photo.query.join(Like).filter(Like.user_id == user.id).all()
    return render_template(
        "profile.html",
        user=user,
        photos=photos,
        saved_photos=saved,
        liked_photos=liked,
    )


@app.route("/upload", methods=["GET", "POST"])
@login_required
def creator_dashboard():
    if current_user.role != "creator":
        flash("Only creators can upload photos.", "warning")
        return redirect(url_for("feed"))

    if request.method == "POST":
        try:
            image = _validated_image(request.files.get("photo"))
            file_url = _store_image(image, f"photo_{current_user.id}")
            auto_tags = analyze_image(image)

            title = (request.form.get("title") or "").strip()
            if not title:
                raise ValueError("A title is required.")

            photo = Photo(
                filename=file_url,
                title=title[:100],
                caption=(request.form.get("caption") or "").strip()[:500],
                location=(request.form.get("location") or "").strip()[:100],
                people_present=(request.form.get("people") or "").strip()[:200],
                auto_tags=auto_tags,
                user_id=current_user.id,
            )
            db.session.add(photo)
            db.session.commit()
            flash("Photo uploaded.", "success")
            return redirect(url_for("profile", username=current_user.username))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception:
            logger.exception("Photo upload failed for user %s", current_user.id)
            flash("Upload failed. Please try again.", "danger")

    return render_template("dashboard.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("role", "consumer")

        if role not in {"consumer", "creator"}:
            flash("Invalid account role.", "danger")
            return redirect(url_for("register"))
        if len(username) < 3 or len(username) > 150:
            flash("Username must be between 3 and 150 characters.", "danger")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))

        user = User(
            username=username,
            role=role,
            password=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        requested_role = request.form.get("role")

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid credentials.", "danger")
            return render_template("login.html"), 401

        if requested_role != user.role:
            flash(f"Incorrect role. This account is registered as {user.role}.", "warning")
            return render_template("login.html"), 403

        login_user(user)
        return redirect(
            url_for("creator_dashboard" if user.role == "creator" else "feed")
        )

    return render_template("login.html")


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        current_user.bio = (request.form.get("bio") or "").strip()[:300]
        avatar = request.files.get("avatar")

        if avatar and avatar.filename:
            try:
                image = _validated_image(avatar)
                current_user.avatar = _store_image(
                    image,
                    f"avatar_{current_user.id}",
                )
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("edit_profile.html"), 400
            except Exception:
                logger.exception("Avatar upload failed for user %s", current_user.id)
                flash("Avatar upload failed.", "danger")
                return render_template("edit_profile.html"), 500

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile", username=current_user.username))

    return render_template("edit_profile.html")


@app.route("/comment/<int:photo_id>", methods=["POST"])
@login_required
def add_comment(photo_id):
    Photo.query.get_or_404(photo_id)
    text = (request.form.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "message": "Comment cannot be empty."}), 400
    if len(text) > 500:
        return jsonify({"success": False, "message": "Comment is too long."}), 400

    score = TextBlob(text).sentiment.polarity
    if score < -0.3:
        return jsonify(
            {
                "success": False,
                "message": "Comment blocked by the sentiment moderation rule.",
            }
        ), 400

    sentiment = "positive" if score >= 0.3 else "negative" if score <= -0.1 else "neutral"

    db.session.add(
        Comment(
            text=text,
            user_id=current_user.id,
            photo_id=photo_id,
        )
    )
    db.session.commit()
    return jsonify(
        {
            "success": True,
            "username": current_user.username,
            "text": text,
            "sentiment": sentiment,
        }
    )


@app.route("/like/<int:photo_id>", methods=["POST"])
@login_required
def toggle_like(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    existing = Like.query.filter_by(
        user_id=current_user.id,
        photo_id=photo_id,
    ).first()

    if existing:
        db.session.delete(existing)
        liked = False
    else:
        db.session.add(Like(user_id=current_user.id, photo_id=photo_id))
        liked = True

    db.session.commit()
    return jsonify({"count": photo.likes.count(), "liked": liked})


@app.route("/save/<int:photo_id>", methods=["POST"])
@login_required
def toggle_save(photo_id):
    Photo.query.get_or_404(photo_id)
    existing = Save.query.filter_by(
        user_id=current_user.id,
        photo_id=photo_id,
    ).first()

    if existing:
        db.session.delete(existing)
        saved = False
    else:
        db.session.add(Save(user_id=current_user.id, photo_id=photo_id))
        saved = True

    db.session.commit()
    return jsonify({"saved": saved})


@app.route("/post/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_post(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if photo.user_id != current_user.id:
        return jsonify({"success": False, "message": "Not authorized."}), 403

    if (
        photo.filename
        and photo.filename.startswith("http")
        and AZURE_CONTAINER_NAME
        and blob_service_client
    ):
        parts = photo.filename.split(f"/{AZURE_CONTAINER_NAME}/", 1)
        if len(parts) == 2:
            try:
                blob_service_client.get_blob_client(
                    container=AZURE_CONTAINER_NAME,
                    blob=parts[1],
                ).delete_blob()
            except Exception:
                logger.exception("Could not delete Azure blob for photo %s", photo_id)
    elif "/static/uploads/" in (photo.filename or ""):
        filename = photo.filename.split("/static/uploads/")[-1]
        local_path = os.path.join(LOCAL_UPLOAD_FOLDER, filename)
        if os.path.isfile(local_path):
            try:
                os.remove(local_path)
            except OSError:
                logger.exception("Could not delete local photo file %s", local_path)

    db.session.delete(photo)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/debug/recent_photos", methods=["GET"])
@login_required
def debug_recent_photos():
    if PRODUCTION:
        abort(404)
    if current_user.role != "creator":
        abort(403)

    photos = Photo.query.order_by(Photo.uploaded_at.desc()).limit(50).all()
    return jsonify(
        [
            {
                "id": photo.id,
                "filename": photo.filename,
                "uploaded_at": photo.uploaded_at.isoformat(),
            }
            for photo in photos
        ]
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/_health")
def health():
    return jsonify(
        {
            "status": "ok",
            "storage": "azure" if blob_service_client else "local",
            "environment": APP_ENV,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
