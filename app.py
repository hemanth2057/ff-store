import os
import random
import sqlite3
import time
import uuid
from functools import wraps
from pathlib import Path
from urllib.parse import quote

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "users.db"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_IMAGES = 10
MAX_SELL_REQUEST_IMAGES = 15


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "ff-store-pro-dev-secret"),
    UPLOAD_FOLDER=str(UPLOAD_DIR),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL", "admin@ffstorepro.com"),
    ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "21@Hemutyh671"),
    PAYMENT_UPI_ID=os.environ.get("PAYMENT_UPI_ID", "paytm.s1qrsuh@pty"),
    PAYMENT_UPI_NAME=os.environ.get("PAYMENT_UPI_NAME", "FF Store Pro"),
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cursor.fetchall())


def ensure_column(cursor, table_name, column_name, definition):
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            original_price REAL NOT NULL DEFAULT 0,
            description TEXT DEFAULT '',
            images TEXT DEFAULT '',
            features TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            full_name TEXT NOT NULL DEFAULT '',
            utr TEXT NOT NULL UNIQUE,
            level INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            approved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sell_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            seller_name TEXT NOT NULL DEFAULT '',
            mobile_number TEXT NOT NULL DEFAULT '',
            images TEXT NOT NULL DEFAULT '',
            bind_email TEXT NOT NULL DEFAULT '',
            account_details TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    ensure_column(cursor, "users", "is_admin", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(cursor, "users", "created_at", "TIMESTAMP")

    ensure_column(cursor, "accounts", "description", "TEXT DEFAULT ''")
    ensure_column(cursor, "accounts", "images", "TEXT DEFAULT ''")
    ensure_column(cursor, "accounts", "features", "TEXT DEFAULT ''")
    ensure_column(cursor, "accounts", "created_at", "TIMESTAMP")
    ensure_column(cursor, "accounts", "original_price", "REAL NOT NULL DEFAULT 0")
    ensure_column(cursor, "accounts", "recovery_email", "TEXT NOT NULL DEFAULT ''")
    ensure_column(cursor, "accounts", "prime_level", "INTEGER NOT NULL DEFAULT 5")

    ensure_column(cursor, "payments", "level", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(cursor, "payments", "status", "TEXT NOT NULL DEFAULT 'pending'")
    ensure_column(cursor, "payments", "created_at", "TIMESTAMP")
    ensure_column(cursor, "payments", "user_id", "INTEGER")
    ensure_column(cursor, "payments", "account_id", "INTEGER")
    ensure_column(cursor, "payments", "full_name", "TEXT NOT NULL DEFAULT ''")
    ensure_column(cursor, "payments", "approved_at", "TIMESTAMP")
    ensure_column(cursor, "payments", "admin_note", "TEXT NOT NULL DEFAULT ''")

    ensure_column(cursor, "sell_requests", "user_id", "INTEGER")
    ensure_column(cursor, "sell_requests", "seller_name", "TEXT NOT NULL DEFAULT ''")
    ensure_column(cursor, "sell_requests", "mobile_number", "TEXT NOT NULL DEFAULT ''")
    ensure_column(cursor, "sell_requests", "prime_level", "INTEGER NOT NULL DEFAULT 5")
    ensure_column(cursor, "sell_requests", "images", "TEXT NOT NULL DEFAULT ''")
    ensure_column(cursor, "sell_requests", "bind_email", "TEXT NOT NULL DEFAULT ''")
    ensure_column(cursor, "sell_requests", "account_details", "TEXT NOT NULL DEFAULT ''")
    ensure_column(cursor, "sell_requests", "status", "TEXT NOT NULL DEFAULT 'pending'")
    ensure_column(cursor, "sell_requests", "created_at", "TIMESTAMP")

    admin_email = app.config["ADMIN_EMAIL"].strip().lower()
    cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    admin_user = cursor.fetchone()
    admin_password_hash = generate_password_hash(app.config["ADMIN_PASSWORD"])

    if admin_user:
        cursor.execute(
            "UPDATE users SET name = ?, password = ?, is_admin = 1 WHERE email = ?",
            ("FF Store Admin", admin_password_hash, admin_email),
        )
    else:
        cursor.execute(
            """
            INSERT INTO users (name, email, password, is_admin)
            VALUES (?, ?, ?, 1)
            """,
            ("FF Store Admin", admin_email, admin_password_hash),
        )

    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)

    return wrapped_view


def user_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        if session.get("admin"):
            return redirect(url_for("admin"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_features(text):
    raw_items = [item.strip() for item in text.replace("\r", "").split("\n")]
    return [item for item in raw_items if item]


def image_list(images_value):
    if not images_value:
        return []
    return [item.strip() for item in images_value.split(",") if item.strip()]


def pick_recovery_email(seed_value=None):
    recovery_emails = [
        "rommfree0@gmail.com",
        "ops862794@gmail.com",
    ]
    rng = random.Random(seed_value) if seed_value is not None else random
    return recovery_emails[rng.randint(0, len(recovery_emails) - 1)]


def build_level2_display_code(seed):
    source = str(seed or "FFSTORE")
    window_stamp = int(time.time() * 1000) // 120000
    hash_value = 0

    for char in source:
        hash_value = ((hash_value * 31) + ord(char) + window_stamp) % 10000000

    code = str(abs(hash_value)).zfill(7)[-7:]
    return f"{code[:4]}***"


def build_level3_display_code(seed):
    source = str(seed or "FFSTORE")
    window_stamp = int(time.time() * 1000) // 60000
    hash_value = 0

    for char in source:
        hash_value = ((hash_value * 41) + ord(char) + window_stamp) % 10000000

    return str(abs(hash_value)).zfill(7)[-7:]


def build_unlock_payload(account):
    product_id = account.get("id") if isinstance(account, dict) else account["id"]
    title = account.get("title", "") if isinstance(account, dict) else account["title"]
    recovery_email = account.get("recovery_email", "") if isinstance(account, dict) else account["recovery_email"]

    if not isinstance(product_id, int):
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            product_id = 0

    title_token = "".join(ch for ch in str(title).upper() if ch.isalnum())[:6] or "PRO"
    code_seed = f"{title_token}{product_id:03d}"
    full_code = f"{code_seed}-{uuid.uuid5(uuid.NAMESPACE_DNS, str(title) or 'FF Store Pro').hex[:8].upper()}"
    level1_email = (recovery_email or "").strip() or pick_recovery_email(product_id)
    return {
        "level1_email": level1_email,
        "level2_code": build_level2_display_code(full_code),
        "level3_code": build_level3_display_code(full_code),
        "level3_seed": full_code,
    }


def pick_original_price(price_value, seed_value=None):
    rng = random.Random(seed_value) if seed_value is not None else random
    base_price = float(price_value)
    original_price = float(rng.randint(5000, 10000))

    if original_price <= base_price:
        original_price = float(max(int(base_price + rng.randint(900, 2800)), int(base_price * 1.25)))

    return round(original_price, 2)


def enrich_account_offer(account):
    account_data = dict(account)
    price_value = float(account_data.get("price") or 0)
    original_price = float(account_data.get("original_price") or 0)

    if original_price <= price_value:
        original_price = pick_original_price(price_value, seed_value=account_data.get("id"))

    discount_percent = 0
    if original_price > 0 and original_price > price_value:
        discount_percent = round(((original_price - price_value) / original_price) * 100)

    account_data["original_price"] = original_price
    account_data["discount_percent"] = max(discount_percent, 0)
    return account_data


def get_payment_amounts(price_value):
    try:
        normalized_price = int(round(float(price_value)))
    except (TypeError, ValueError):
        normalized_price = 399

    if normalized_price == 499:
        return {1: 499, 2: 999, 3: 1499}

    return {1: 399, 2: 899, 3: 1399}


def build_payment_upi_link(amount):
    payment_upi_id = app.config["PAYMENT_UPI_ID"]
    payment_upi_name = app.config["PAYMENT_UPI_NAME"]
    return f"upi://pay?pa={payment_upi_id}&pn={quote(payment_upi_name)}&am={int(amount)}&cu=INR"


def build_payment_qr_url(amount):
    return f"https://api.qrserver.com/v1/create-qr-code/?size=320x320&data={quote(build_payment_upi_link(amount), safe='')}"


def build_listing_copy(price_value, title_hint="", variant=0):
    normalized_price = int(round(float(price_value)))
    title_seed = (title_hint or "").strip()
    plan_label = "Rs. 499" if normalized_price == 499 else "Rs. 399"

    if normalized_price == 499:
        title_lead = ["Premium", "Trusted", "Elite", "Secure", "Exclusive", "High Value", "Priority", "Professional"]
        title_core = ["Shared Access", "Recovery Ready", "Account Recovery", "Login Access", "Game Access", "Premium Access"]
        title_tail = ["Account", "Profile", "Plan", "Bundle", "Listing", "Package", "Edition"]
        openers = ["Trusted", "Professional", "Premium", "Secure", "Buyer-focused", "Store-ready", "Reliable", "Refined"]
        middles = ["shared access flow", "recovery-ready setup", "level-based unlock structure", "clean payment journey", "premium purchase flow", "account detail presentation"]
        trust_points = ["clear buyer guidance", "stronger trust presentation", "polished access details", "professional unlock steps", "cleaner delivery structure", "confident storefront wording"]
        closers = ["built for serious buyers.", "designed for premium listings.", "ready for a professional storefront.", "made to improve buyer confidence.", "prepared for a smoother recovery handoff.", "optimized for clear account details."]
    else:
        title_lead = ["Trusted", "Secure", "Starter", "Professional", "Reliable", "Smart", "Clean", "Buyer Ready"]
        title_core = ["Shared Access", "Recovery Ready", "Entry Access", "Starter Recovery", "Login Access", "Account Access"]
        title_tail = ["Account", "Plan", "Listing", "Package", "Bundle", "Profile", "Option"]
        openers = ["Reliable", "Professional", "Secure", "Trusted", "Buyer-friendly", "Store-ready", "Clean", "Balanced"]
        middles = ["shared access flow", "entry recovery setup", "fixed unlock payment structure", "simple premium storefront flow", "guided account access process", "clean purchase journey"]
        trust_points = ["clear account details", "strong buyer trust", "simple unlock guidance", "professional payment steps", "clean access presentation", "consistent recovery flow"]
        closers = ["built for everyday buyers.", "designed for cleaner listings.", "made for simple premium presentation.", "ready for mobile and desktop storefronts.", "optimized for trust and clarity.", "prepared for a smoother purchase flow."]

    title_options = [
        f"{lead} {core} {tail}"
        for lead in title_lead
        for core in title_core
        for tail in title_tail
    ]
    seed = (variant + normalized_price + len(title_seed)) % 9973
    return {
        "title": title_seed or title_options[seed % len(title_options)],
        "description": f"{openers[seed % len(openers)]} {plan_label} account with a {middles[(seed + 3) % len(middles)]} and {trust_points[(seed + 7) % len(trust_points)]}. {openers[(seed + 11) % len(openers)]} listing {closers[(seed + 17) % len(closers)]}",
    }


def current_user():
    if not session.get("user_id"):
        return None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, is_admin FROM users WHERE id = ?",
        (session["user_id"],),
    )
    user = cursor.fetchone()
    conn.close()
    return user


@app.context_processor
def inject_globals():
    payment_upi_id = app.config["PAYMENT_UPI_ID"]
    payment_upi_name = app.config["PAYMENT_UPI_NAME"]
    payment_upi_link = build_payment_upi_link(399)
    payment_qr_url = build_payment_qr_url(399)
    asset_version = int(Path(__file__).stat().st_mtime)
    return {
        "current_user": current_user(),
        "payment_upi_id": payment_upi_id,
        "payment_upi_name": payment_upi_name,
        "payment_upi_link": payment_upi_link,
        "payment_qr_url": payment_qr_url,
        "asset_version": asset_version,
    }


@app.route("/")
def home():
    return redirect(url_for("login_page"))


@app.route("/login", methods=["GET"])
def login_page():
    if session.get("user_id") and not session.get("admin"):
        return redirect(url_for("dashboard"))
    if session.get("admin"):
        return redirect(url_for("admin"))
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()

    if len(name) < 2:
        return jsonify({"status": "error", "message": "Name is required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(?) AND is_admin = 0 ORDER BY id ASC", (name,))
    user = cursor.fetchone()

    if not user:
        slug = "".join(char.lower() if char.isalnum() else "" for char in name) or "player"
        synthetic_email = f"{slug}-{uuid.uuid4().hex[:8]}@guest.ffstore.local"
        password_hash = generate_password_hash(uuid.uuid4().hex)
        cursor.execute(
            "INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 0)",
            (name, synthetic_email, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
    else:
        user_id = user["id"]

    conn.close()

    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    session["admin"] = False
    return jsonify({"status": "success", "redirect": url_for("dashboard")})


@app.route("/signup", methods=["POST"])
def signup():
    return login()


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/dashboard")
@user_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts ORDER BY id DESC")
    accounts = [enrich_account_offer(row) for row in cursor.fetchall()]
    cursor.execute(
        """
        SELECT COUNT(DISTINCT account_id) AS total
        FROM payments
        WHERE user_id = ? AND status = 'approved'
        """,
        (session["user_id"],),
    )
    history_count = cursor.fetchone()["total"]
    conn.close()
    return render_template(
        "dashboard.html",
        accounts=accounts,
        image_list=image_list,
        history_count=history_count,
    )


@app.route("/history")
@user_required
def history():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT payments.*, accounts.title AS account_title, accounts.description AS account_description,
               accounts.images AS account_images, accounts.recovery_email AS account_recovery_email
        FROM payments
        LEFT JOIN accounts ON accounts.id = payments.account_id
        WHERE payments.user_id = ? AND payments.status = 'approved'
        ORDER BY COALESCE(payments.approved_at, payments.created_at) DESC
        """,
        (session["user_id"],),
    )
    rows = cursor.fetchall()
    conn.close()

    purchases_by_account = {}
    for row in rows:
        payment = dict(row)
        payment["account_title"] = payment.get("account_title") or "Purchased Account"
        payment["account_description"] = payment.get("account_description") or "Approved purchase"
        payment["account_images"] = image_list(payment.get("account_images"))
        account_id = payment.get("account_id") or 0
        existing_purchase = purchases_by_account.get(account_id)

        if not existing_purchase:
            purchases_by_account[account_id] = payment
            continue

        existing_level = int(existing_purchase.get("level") or 0)
        current_level = int(payment.get("level") or 0)

        if current_level > existing_level:
            existing_purchase["level"] = current_level
            existing_purchase["utr"] = payment.get("utr")

        existing_approved_at = existing_purchase.get("approved_at") or existing_purchase.get("created_at") or ""
        current_approved_at = payment.get("approved_at") or payment.get("created_at") or ""
        if current_approved_at > existing_approved_at:
            existing_purchase["approved_at"] = payment.get("approved_at")
            existing_purchase["created_at"] = payment.get("created_at")

    purchases = list(purchases_by_account.values())

    for payment in purchases:
        payment["approved_unlock"] = build_unlock_payload(
            {
                "id": payment.get("account_id") or 0,
                "title": payment["account_title"],
                "recovery_email": payment.get("account_recovery_email") or "",
            }
        )

    return render_template("history.html", purchases=purchases)


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_admin = 1", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["admin"] = True
            return redirect(url_for("admin"))

        error = "Invalid admin email or password."

    return render_template(
        "admin_login.html",
        error=error,
        admin_email_hint=app.config["ADMIN_EMAIL"],
    )


@app.route("/admin")
@admin_required
def admin():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts ORDER BY id DESC")
    accounts = cursor.fetchall()
    conn.close()
    return render_template(
        "admin.html",
        accounts=accounts,
        image_list=image_list,
    )


@app.route("/add_account", methods=["POST"])
@admin_required
def add_account():
    title = request.form.get("title", "").strip()
    price = request.form.get("price", "").strip()
    prime_level = request.form.get("prime_level", "5").strip()
    description = request.form.get("description", "").strip()
    files = request.files.getlist("images")

    if not title or not price:
        flash("Title and price are required to add an account.", "error")
        return redirect(url_for("admin"))

    if len([file for file in files if file and file.filename]) > MAX_IMAGES:
        flash(f"You can upload up to {MAX_IMAGES} images per account.", "error")
        return redirect(url_for("admin"))

    image_paths = []
    for file in files:
        if not file or not file.filename:
            continue

        if not allowed_file(file.filename):
            continue

        extension = secure_filename(file.filename).rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{extension}"
        destination = UPLOAD_DIR / filename
        file.save(destination)
        image_paths.append(f"uploads/{filename}")

    conn = get_db()
    cursor = conn.cursor()
    try:
        price_value = float(price)
    except ValueError:
        conn.close()
        for image_path in image_paths:
            saved_file = STATIC_DIR / image_path
            if saved_file.exists():
                saved_file.unlink()
        flash("Choose a valid account price before publishing.", "error")
        return redirect(url_for("admin"))

    try:
        prime_level_value = int(prime_level)
    except ValueError:
        conn.close()
        for image_path in image_paths:
            saved_file = STATIC_DIR / image_path
            if saved_file.exists():
                saved_file.unlink()
        flash("Choose a valid prime level.", "error")
        return redirect(url_for("admin"))

    if int(round(price_value)) not in {399, 499}:
        conn.close()
        for image_path in image_paths:
            saved_file = STATIC_DIR / image_path
            if saved_file.exists():
                saved_file.unlink()
        flash("Only Rs. 399 and Rs. 499 plans are allowed.", "error")
        return redirect(url_for("admin"))

    if prime_level_value not in {5, 6, 7, 8}:
        conn.close()
        for image_path in image_paths:
            saved_file = STATIC_DIR / image_path
            if saved_file.exists():
                saved_file.unlink()
        flash("Prime level must be 5, 6, 7, or 8.", "error")
        return redirect(url_for("admin"))

    original_price = pick_original_price(price_value)
    recovery_email = pick_recovery_email()

    try:
        cursor.execute(
            """
            INSERT INTO accounts (title, price, original_price, description, images, features, recovery_email, prime_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                price_value,
                original_price,
                description,
                ",".join(image_paths),
                "",
                recovery_email,
                prime_level_value,
            ),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        for image_path in image_paths:
            saved_file = STATIC_DIR / image_path
            if saved_file.exists():
                saved_file.unlink()
        flash("The account could not be saved. Please try again.", "error")
        conn.close()
        return redirect(url_for("admin"))

    conn.close()
    flash("Account added successfully.", "success")

    return redirect(url_for("admin"))


@app.route("/submit_sell_request", methods=["POST"])
@user_required
def submit_sell_request():
    seller_name = request.form.get("seller_name", "").strip()
    mobile_number = request.form.get("mobile_number", "").strip()
    prime_level = request.form.get("prime_level", "5").strip()
    bind_email = request.form.get("bind_email", "").strip().lower()
    account_details = request.form.get("account_details", "").strip()
    files = request.files.getlist("images")

    if not seller_name or not mobile_number or not bind_email or not account_details:
        flash("Fill in your name, mobile number, prime level, bind mail, and account details.", "error")
        return redirect(url_for("dashboard"))

    if len([file for file in files if file and file.filename]) > MAX_SELL_REQUEST_IMAGES:
        flash(f"You can upload up to {MAX_SELL_REQUEST_IMAGES} selling images.", "error")
        return redirect(url_for("dashboard"))

    try:
        prime_level_value = int(prime_level)
    except ValueError:
        flash("Choose a valid prime level.", "error")
        return redirect(url_for("dashboard"))

    if prime_level_value not in {5, 6, 7, 8}:
        flash("Prime level must be 5, 6, 7, or 8.", "error")
        return redirect(url_for("dashboard"))

    image_paths = []
    for file in files:
        if not file or not file.filename:
            continue

        if not allowed_file(file.filename):
            continue

        extension = secure_filename(file.filename).rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{extension}"
        destination = UPLOAD_DIR / filename
        file.save(destination)
        image_paths.append(f"uploads/{filename}")

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO sell_requests (user_id, seller_name, mobile_number, prime_level, images, bind_email, account_details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                seller_name,
                mobile_number,
                prime_level_value,
                ",".join(image_paths),
                bind_email,
                account_details,
            ),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        for image_path in image_paths:
            saved_file = STATIC_DIR / image_path
            if saved_file.exists():
                saved_file.unlink()
        conn.close()
        flash("The selling request could not be saved. Please try again.", "error")
        return redirect(url_for("dashboard"))
    conn.close()

    flash("Your FF account sell request was sent to admin.", "success")
    return redirect(url_for("dashboard"))


@app.route("/approve_sell_request/<int:request_id>", methods=["POST"])
@admin_required
def approve_sell_request(request_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM sell_requests WHERE id = ?", (request_id,))
    sell_request = cursor.fetchone()

    if not sell_request:
        conn.close()
        return redirect(url_for("admin"))

    if sell_request["status"] != "approved":
        cursor.execute(
            """
            UPDATE sell_requests
            SET status = 'approved'
            WHERE id = ?
            """,
            (request_id,),
        )
        conn.commit()

    conn.close()
    flash("Sell request approved.", "success")
    return redirect(url_for("admin_selling_accounts"))


@app.route("/reject_sell_request/<int:request_id>", methods=["POST"])
@admin_required
def reject_sell_request(request_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM sell_requests WHERE id = ?", (request_id,))
    sell_request = cursor.fetchone()

    if not sell_request:
        conn.close()
        return redirect(url_for("admin"))

    if sell_request["status"] != "rejected":
        cursor.execute(
            """
            UPDATE sell_requests
            SET status = 'rejected'
            WHERE id = ?
            """,
            (request_id,),
        )
        conn.commit()

    conn.close()
    flash("Sell request rejected.", "success")
    return redirect(url_for("admin_selling_accounts"))


@app.route("/admin_selling_accounts")
@admin_required
def admin_selling_accounts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sell_requests.*, users.name AS user_name, users.email AS user_email
        FROM sell_requests
        LEFT JOIN users ON users.id = sell_requests.user_id
        ORDER BY sell_requests.id DESC
        """
    )
    sell_requests = cursor.fetchall()
    conn.close()
    return render_template(
        "selling_accounts.html",
        sell_requests=sell_requests,
        image_list=image_list,
    )

@app.route("/delete_account/<int:account_id>", methods=["POST"])
@admin_required
def delete_account(account_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT images FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()

    if account:
        for image_path in image_list(account["images"]):
            file_path = STATIC_DIR / image_path
            if file_path.exists():
                file_path.unlink()

    cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/bulk_delete_accounts", methods=["POST"])
@admin_required
def bulk_delete_accounts():
    account_ids = request.form.getlist("account_ids")
    normalized_ids = []

    for account_id in account_ids:
        try:
            normalized_ids.append(int(account_id))
        except (TypeError, ValueError):
            continue

    if not normalized_ids:
        return redirect(url_for("admin"))

    conn = get_db()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in normalized_ids)
    cursor.execute(f"SELECT images FROM accounts WHERE id IN ({placeholders})", normalized_ids)
    accounts = cursor.fetchall()

    for account in accounts:
        for image_path in image_list(account["images"]):
            file_path = STATIC_DIR / image_path
            if file_path.exists():
                file_path.unlink()

    cursor.execute(f"DELETE FROM accounts WHERE id IN ({placeholders})", normalized_ids)
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/edit_account/<int:account_id>", methods=["GET", "POST"])
@admin_required
def edit_account(account_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()

    if not account:
        conn.close()
        return redirect(url_for("admin"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        price = request.form.get("price", "").strip()
        prime_level = request.form.get("prime_level", "5").strip()
        description = request.form.get("description", "").strip()

        try:
            price_value = float(price)
        except ValueError:
            conn.close()
            return redirect(url_for("edit_account", account_id=account_id))

        try:
            prime_level_value = int(prime_level)
        except ValueError:
            conn.close()
            return redirect(url_for("edit_account", account_id=account_id))

        if not title or int(round(price_value)) not in {399, 499} or prime_level_value not in {5, 6, 7, 8}:
            conn.close()
            return redirect(url_for("edit_account", account_id=account_id))

        cursor.execute(
            """
            UPDATE accounts
            SET title = ?, price = ?, description = ?, prime_level = ?
            WHERE id = ?
            """,
            (title, price_value, description, prime_level_value, account_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    conn.close()
    return render_template("edit_account.html", account=account)


@app.route("/product/<int:account_id>")
@user_required
def product(account_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()

    if not account:
        conn.close()
        return redirect(url_for("dashboard"))

    account = enrich_account_offer(account)
    images = image_list(account["images"])
    features = parse_features(account["features"]) or [
        "Rare bundles and premium cosmetics",
        "Secure instant delivery",
        "Hand-checked listing",
    ]
    unlock_payload = build_unlock_payload(account)
    cursor.execute(
        """
        SELECT COALESCE(MAX(level), 0) AS approved_level
        FROM payments
        WHERE user_id = ? AND account_id = ? AND status = 'approved'
        """,
        (session["user_id"], account_id),
    )
    approved_payment = cursor.fetchone()
    approved_level = approved_payment["approved_level"] if approved_payment else 0
    next_payment_level = min(approved_level + 1, 3) if approved_level < 3 else 3
    cursor.execute(
        """
        SELECT status, level, admin_note
        FROM payments
        WHERE user_id = ? AND account_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session["user_id"], account_id),
    )
    latest_payment = cursor.fetchone()
    payment_popup = None
    if latest_payment:
        payment_status = (latest_payment["status"] or "").lower()
        payment_note = (latest_payment["admin_note"] or "").strip()
        if payment_status == "rejected":
            payment_popup = {
                "tone": "error",
                "title": "Payment Rejected",
                "message": payment_note or "UTR is invalid. Please pay again.",
            }
        elif payment_status == "approved":
            payment_popup = {
                "tone": "success",
                "title": "Payment Approved",
                "message": payment_note or "The account is ready for you.",
            }
    payment_amounts = get_payment_amounts(account["price"])
    payment_qr_url = build_payment_qr_url(payment_amounts[next_payment_level])
    conn.close()

    return render_template(
        "product.html",
        account=account,
        images=images,
        features=features,
        unlock_payload=unlock_payload,
        approved_level=approved_level,
        next_payment_level=next_payment_level,
        payment_amounts=payment_amounts,
        payment_qr_url=payment_qr_url,
        payment_popup=payment_popup,
    )


@app.route("/submit_payment", methods=["POST"])
@user_required
def submit_payment():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    full_name = str(data.get("full_name", "")).strip()
    utr = str(data.get("utr", "")).strip()
    level = int(data.get("level", 1))

    if level not in {1, 2, 3}:
        return jsonify({"status": "error", "message": "Invalid unlock level."}), 400

    if len(full_name) < 3:
        return jsonify({"status": "error", "message": "Full name is required."}), 400

    if (
        not utr.isdigit()
        or len(utr) != 12
        or len(set(utr)) == 1
        or utr in "012345678901234567890123456789"
        or utr in "987654321098765432109876543210"
        or utr.startswith("0")
    ):
        return jsonify({"status": "error", "message": "Enter a strict valid 12-digit UTR code."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()

    if not account:
        conn.close()
        return jsonify({"status": "error", "message": "Product not found."}), 404

    cursor.execute("SELECT id FROM payments WHERE utr = ?", (utr,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "That UTR has already been used."}), 409

    cursor.execute(
        """
        INSERT INTO payments (user_id, account_id, full_name, utr, level, status, admin_note)
        VALUES (?, ?, ?, ?, ?, 'pending', '')
        """,
        (session["user_id"], account_id, full_name, utr, level),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            "status": "success",
            "level": level,
            "message": f"Payment for Level {level} submitted. Waiting for admin approval.",
        }
    )


@app.route("/payment_status/<int:account_id>")
@user_required
def payment_status(account_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()

    if not account:
        conn.close()
        return jsonify({"status": "error", "message": "Product not found."}), 404

    cursor.execute(
        """
        SELECT COALESCE(MAX(level), 0) AS approved_level
        FROM payments
        WHERE user_id = ? AND account_id = ? AND status = 'approved'
        """,
        (session["user_id"], account_id),
    )
    approved_payment = cursor.fetchone()
    approved_level = approved_payment["approved_level"] if approved_payment else 0
    next_payment_level = min(approved_level + 1, 3) if approved_level < 3 else 3

    cursor.execute(
        """
        SELECT status, level, admin_note
        FROM payments
        WHERE user_id = ? AND account_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session["user_id"], account_id),
    )
    latest_payment = cursor.fetchone()
    conn.close()

    return jsonify(
        {
            "status": "success",
            "approved_level": approved_level,
            "next_payment_level": next_payment_level,
            "latest_payment_status": (latest_payment["status"] if latest_payment else ""),
            "latest_payment_level": (latest_payment["level"] if latest_payment else 0),
            "latest_payment_note": (latest_payment["admin_note"] if latest_payment else ""),
            "unlock": build_unlock_payload(account),
        }
    )


@app.route("/approve_payment/<int:payment_id>", methods=["POST"])
@admin_required
def approve_payment(payment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM payments WHERE id = ?", (payment_id,))
    payment = cursor.fetchone()

    if not payment:
        conn.close()
        return redirect(url_for("admin_payments"))

    if payment["status"] != "approved":
        cursor.execute(
            """
            UPDATE payments
            SET status = 'approved', approved_at = CURRENT_TIMESTAMP, admin_note = 'The account is ready for you.'
            WHERE id = ?
            """,
            (payment_id,),
        )
        conn.commit()

    conn.close()
    return redirect(url_for("admin_payments"))


@app.route("/reject_payment/<int:payment_id>", methods=["POST"])
@admin_required
def reject_payment(payment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM payments WHERE id = ?", (payment_id,))
    payment = cursor.fetchone()

    if payment:
        cursor.execute(
            """
            UPDATE payments
            SET status = 'rejected', admin_note = 'UTR is invalid. Please pay again.', approved_at = NULL
            WHERE id = ?
            """,
            (payment_id,),
        )
        conn.commit()

    conn.close()
    return redirect(url_for("admin_payments"))


@app.route("/delete_payment/<int:payment_id>", methods=["POST"])
@admin_required
def delete_payment(payment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_payments"))

@app.route('/google49342162f06c9265.html')
def verify():
    return app.send_static_file('google49342162f06c9265.html')

@app.route('/sitemap.xml')
def sitemap():
    return app.send_static_file('sitemap.xml')


@app.route("/admin_payments")
@admin_required
def admin_payments():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT payments.*, users.email AS user_email, accounts.title AS account_title,
               accounts.recovery_email AS account_recovery_email
        FROM payments
        LEFT JOIN users ON users.id = payments.user_id
        LEFT JOIN accounts ON accounts.id = payments.account_id
        ORDER BY payments.id DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    payments = []
    for row in rows:
        payment = dict(row)
        payment["full_name"] = (payment.get("full_name") or "").strip() or "Not provided"
        payment["user_email"] = payment.get("user_email") or "Unknown user"
        payment["account_title"] = payment.get("account_title") or "Deleted listing"
        payment["status"] = (payment.get("status") or "pending").lower()
        if payment["status"] == "approved":
            account = {
                "id": payment.get("account_id") or 0,
                "title": payment["account_title"] or "",
                "recovery_email": payment.get("account_recovery_email") or "",
            }
            unlock_payload = build_unlock_payload(account)
            payment["approved_unlock"] = unlock_payload
        else:
            payment["approved_unlock"] = None
        payments.append(payment)

    return render_template("payments.html", payments=payments)


init_db()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
