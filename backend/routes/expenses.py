import hashlib
import json
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from backend.db import get_db
from backend.models import ValidationError, format_paise, parse_amount_to_paise


expenses_bp = Blueprint("expenses", __name__)


def error_response(status_code, error, message):
    return jsonify({"error": error, "message": message}), status_code


def utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise ValidationError("Invalid input: request body must be a JSON object")

    missing = [field for field in ("amount", "category", "description", "date") if field not in payload]
    if missing:
        raise ValidationError(f"Invalid input: missing required field {missing[0]}")

    amount_paise = parse_amount_to_paise(payload["amount"])
    if not isinstance(payload["category"], str):
        raise ValidationError("Invalid input: category is required")
    if not isinstance(payload["description"], str):
        raise ValidationError("Invalid input: description is required")

    category = payload["category"].strip()
    description = payload["description"].strip()
    expense_date = str(payload["date"]).strip()

    # Presence/type checks above do not catch empty or whitespace-only strings.
    if not category:
        raise ValidationError("Invalid input: category is required")
    if not description:
        raise ValidationError("Invalid input: description is required")

    try:
        parsed_date = date.fromisoformat(expense_date)
    except ValueError:
        raise ValidationError("Invalid input: date must be a valid YYYY-MM-DD date") from None

    return {
        "amount_paise": amount_paise,
        "category": category,
        "description": description,
        "date": parsed_date.isoformat(),
    }


def request_hash(normalized):
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def serialize_expense(row):
    return {
        "id": row["id"],
        "amount": format_paise(row["amount_paise"]),
        "amount_paise": row["amount_paise"],
        "category": row["category"],
        "description": row["description"],
        "date": row["date"],
        "created_at": row["created_at"],
    }

# POST /expenses endpoint
@expenses_bp.post("/expenses")
def create_expense():
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    if not idempotency_key:
        return error_response(
            400,
            "VALIDATION_ERROR",
            "Invalid input: Idempotency-Key header is required",
        )

    payload = request.get_json(silent=True)
    if payload is None:
        return error_response(400, "VALIDATION_ERROR", "Invalid input: request body must be valid JSON")

    try:
        normalized = validate_payload(payload)
    except ValidationError as exc:
        return error_response(400, "VALIDATION_ERROR", str(exc))

    payload_hash = request_hash(normalized)
    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            """
            SELECT request_hash, response_json, status_code
            FROM idempotency_keys
            WHERE key = ?
            """,
            (idempotency_key,),
        ).fetchone()

        if existing:
            conn.commit()
            if existing["request_hash"] != payload_hash:
                return error_response(
                    409,
                    "IDEMPOTENCY_KEY_CONFLICT",
                    "The provided Idempotency-Key was used with a different request body.",
                )
            return (
                jsonify(json.loads(existing["response_json"])),
                existing["status_code"],
            )

        created_at = utc_timestamp()
        cursor = conn.execute(
            """
            INSERT INTO expenses (amount_paise, category, description, date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                normalized["amount_paise"],
                normalized["category"],
                normalized["description"],
                normalized["date"],
                created_at,
            ),
        )
        expense_id = cursor.lastrowid
        row = conn.execute(
            """
            SELECT id, amount_paise, category, description, date, created_at
            FROM expenses
            WHERE id = ?
            """,
            (expense_id,),
        ).fetchone()
        response_body = serialize_expense(row)
        response_json = json.dumps(response_body, sort_keys=True, separators=(",", ":"))

        conn.execute(
            """
            INSERT INTO idempotency_keys
                (key, request_hash, expense_id, response_json, status_code, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (idempotency_key, payload_hash, expense_id, response_json, 201, created_at),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return jsonify(response_body), 201

# GET /expenses endpoint with optional category filter and date_desc sorting
@expenses_bp.get("/expenses")
def list_expenses():
    category = request.args.get("category")
    sort = request.args.get("sort")

    params = []
    where_clause = ""

    if category is not None:
        category = category.strip()
        if not category:
            return error_response(
                400,
                "VALIDATION_ERROR",
                "Invalid input: category filter cannot be blank",
            )
        where_clause = "WHERE LOWER(category) = LOWER(?)"
        params.append(category)

    if sort is not None and sort != "date_desc":
        return error_response(400, "VALIDATION_ERROR", "Invalid input: sort must be date_desc")

    order_clause = "ORDER BY date DESC, created_at DESC, id DESC"
    conn = get_db()
    rows = conn.execute(
        f"""
        SELECT id, amount_paise, category, description, date, created_at
        FROM expenses
        {where_clause}
        {order_clause}
        """,
        params,
    ).fetchall()

    total_paise = sum(row["amount_paise"] for row in rows)

    return jsonify(
        {
            "expenses": [serialize_expense(row) for row in rows],
            "total": format_paise(total_paise),
            "total_paise": total_paise,
        }
    )