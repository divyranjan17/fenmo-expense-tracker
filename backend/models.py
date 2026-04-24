from decimal import Decimal, InvalidOperation


MAX_AMOUNT_PAISE = 100_000_000_000
PAISE_PER_UNIT = 100


class ValidationError(ValueError):
    pass


def parse_amount_to_paise(value):
    if isinstance(value, bool) or isinstance(value, float) or value is None:
        raise ValidationError("amount must be a string or integer with at most two decimal places")

    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        raise ValidationError("amount must be numeric") from None

    if not amount.is_finite():
        raise ValidationError("amount must be finite")
    if amount <= 0:
        raise ValidationError("amount must be positive")
    if amount.as_tuple().exponent < -2:
        raise ValidationError("amount must have at most two decimal places")

    paise = int(amount * PAISE_PER_UNIT)
    if paise > MAX_AMOUNT_PAISE:
        raise ValidationError("amount exceeds the maximum allowed value")
    return paise


def format_paise(paise):
    units, cents = divmod(paise, PAISE_PER_UNIT)
    return f"{units}.{cents:02d}"
