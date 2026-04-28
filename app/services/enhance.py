import logging
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


def enhance_image(image: Image.Image) -> Image.Image:
    """图像增强：去噪、对比度调整、光照校正。增强失败时返回原始图片。"""
    try:
        denoised = image.filter(ImageFilter.MedianFilter(size=3))
        contrast = ImageEnhance.Contrast(denoised)
        enhanced = contrast.enhance(1.5)
        brightness = ImageEnhance.Brightness(enhanced)
        enhanced = brightness.enhance(1.2)
        return enhanced
    except Exception as e:
        logger.warning(f"图像增强失败，返回原始图片: {e}")
        return image