"""Upload validation and optimisation shared by product photos and profile avatars."""
import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
Image.MAX_IMAGE_PIXELS = 50_000_000  # guards against decompression bombs


def validate_file_size(f):
    if f.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Image is too large (maximum 5 MB).")


IMAGE_VALIDATORS = [FileExtensionValidator(ALLOWED_EXTENSIONS), validate_file_size]


def _path(folder, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"{folder}/{uuid.uuid4().hex}.{ext}"  # random names: no collisions, no user-controlled paths


def product_image_path(instance, filename):
    return _path("products", filename)


def avatar_path(instance, filename):
    return _path("avatars", filename)


def optimize_image(file, max_side=1600, quality=85):
    """Verify the file is a real image, fix rotation, downscale, strip metadata, re-encode."""
    try:
        file.seek(0)
        img = Image.open(file)
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("Upload a valid image.") from exc
    img = ImageOps.exif_transpose(img)
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img.convert("RGBA").save(buf, "PNG", optimize=True)
        ext = "png"
    else:
        img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
        ext = "jpg"
    return ContentFile(buf.getvalue(), name=f"{uuid.uuid4().hex}.{ext}")


def about_path(instance, filename):
    return _path("about", filename)
