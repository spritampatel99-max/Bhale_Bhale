from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

validate_image_extension = FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"])


def validate_image_size(file):
    limit = settings.MAX_IMAGE_UPLOAD_BYTES
    if file.size > limit:
        raise ValidationError(f"Image is too large ({file.size / 1048576:.1f} MB). Maximum is {limit / 1048576:.0f} MB.")


def _safe_path(folder, filename):
    # Never trust the user's filename: generate a random one and keep only a
    # whitelisted extension.
    ext = Path(filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    return f"{folder}/{uuid4().hex}{ext}"


def product_image_path(instance, filename):
    return _safe_path("products", filename)


def category_image_path(instance, filename):
    return _safe_path("categories", filename)
