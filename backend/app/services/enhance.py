import logging
import os
import time
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from rembg import remove

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENHANCED_DIR = BASE_DIR / "data" / "enhanced"
ENHANCED_DIR.mkdir(parents=True, exist_ok=True)


def enhance_image(image: Image.Image, save_comparison: bool = True, original_filename: str = None) -> Image.Image:
    """图像增强：去噪、对比度调整、光照校正、背景替换为白色。增强失败时返回原始图片。

    Args:
        image: 输入的图片
        save_comparison: 是否保存原图和增强图的对比拼接图
        original_filename: 原始文件名，用于生成保存文件名

    Returns:
        处理后的白底图片
    """
    try:
        denoised = image.filter(ImageFilter.MedianFilter(size=3))
        contrast = ImageEnhance.Contrast(denoised)
        enhanced = contrast.enhance(1.5)
        brightness = ImageEnhance.Brightness(enhanced)
        enhanced = brightness.enhance(1.2)

        enhanced = remove_background_to_white(enhanced)

        if save_comparison:
            save_comparison_image(image, enhanced, original_filename)

        return enhanced
    except Exception as e:
        logger.warning(f"图像增强失败，返回原始图片: {e}")
        return image


def remove_background_to_white(image: Image.Image) -> Image.Image:
    """使用RMBG2.0移除背景并替换为白色"""
    try:
        image_with_alpha = remove(image)

        white_background = Image.new("RGB", image_with_alpha.size, (255, 255, 255))

        if image_with_alpha.mode == 'RGBA':
            white_background.paste(image_with_alpha, mask=image_with_alpha.split()[3])
        else:
            white_background = image_with_alpha.convert("RGB")

        return white_background
    except Exception as e:
        logger.warning(f"背景移除失败，返回增强后的图片: {e}")
        return image


def save_comparison_image(original_image: Image.Image, enhanced_image: Image.Image, original_filename: str = None) -> str:
    """保存原图和增强图的左右对比拼接图到 data/enhanced 目录

    Args:
        original_image: 原始图片
        enhanced_image: 增强后的白底图片
        original_filename: 原始文件名，用于生成新文件名

    Returns:
        保存的文件路径
    """
    try:
        timestamp = int(time.time() * 1000)

        if original_filename:
            filename_without_ext = Path(original_filename).stem
            ext = Path(original_filename).suffix or ".jpg"
            saved_filename = f"{timestamp}_{filename_without_ext}_comparison{ext}"
        else:
            saved_filename = f"{timestamp}_comparison.jpg"

        save_path = ENHANCED_DIR / saved_filename

        width, height = original_image.size
        
        comparison_image = Image.new('RGB', (width * 2, height), (255, 255, 255))
        
        if original_image.mode != 'RGB':
            original_rgb = original_image.convert('RGB')
        else:
            original_rgb = original_image
        
        if enhanced_image.mode != 'RGB':
            enhanced_rgb = enhanced_image.convert('RGB')
        else:
            enhanced_rgb = enhanced_image
        
        comparison_image.paste(original_rgb, (0, 0))
        comparison_image.paste(enhanced_rgb, (width, 0))
        
        comparison_image.save(save_path, quality=95)
        logger.info(f"对比图已保存: {save_path}")

        return str(save_path)
    except Exception as e:
        logger.error(f"保存对比图失败: {e}")
        return None
