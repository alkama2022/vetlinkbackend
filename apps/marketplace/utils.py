import io
from PIL import Image


ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_VIDEO_TYPES = {'video/mp4'}
ALLOWED_DOC_TYPES = {'application/pdf'}


def validate_file_size(f, max_mb: int):
    size_mb = f.size / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(f'File too large: {size_mb:.2f}MB > {max_mb}MB')


def validate_content_type(f, allowed_types: set):
    content_type = getattr(f, 'content_type', None)
    if content_type not in allowed_types:
        raise ValueError(f'Unsupported content type: {content_type}')


def resize_image_file(f, max_width=1600, quality=85):
    try:
        image = Image.open(f)
    except Exception:
        raise ValueError('Invalid image file')

    if image.width <= max_width:
        # rewind file and return original
        f.seek(0)
        return f

    ratio = max_width / float(image.width)
    new_height = int(image.height * ratio)
    image = image.resize((max_width, new_height), Image.LANCZOS)

    out = io.BytesIO()
    format = 'JPEG' if image.mode in ('RGB', 'L', 'P') else 'PNG'
    if format == 'JPEG':
        image = image.convert('RGB')
    image.save(out, format=format, quality=quality)
    out.seek(0)
    out.name = getattr(f, 'name', 'resized.jpg')
    return out
