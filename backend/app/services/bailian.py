from typing import Optional, List
import io
import logging
import base64
import time
from PIL import Image
from openai import OpenAI
from app.config import BAILIAN_API_KEY, BAILIAN_BASE_URL, BAILIAN_MODEL_NAME, BAILIAN_TIMEOUT

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=BAILIAN_API_KEY,
            base_url=BAILIAN_BASE_URL,
            timeout=BAILIAN_TIMEOUT,
        )
    return _client


def _call_api(image: Image.Image, prompt: str, max_retries: int = 3) -> object:
    """调用百炼多模态API，返回原始响应对象。包含重试机制。"""
    client = _get_client()
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=BAILIAN_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            return response
        except Exception as e:
            last_error = e
            logger.warning(f"百炼API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5
                time.sleep(wait_time)
    
    raise last_error


def _get_categories() -> List[str]:
    """延迟获取底库类别列表。"""
    from app.services.pipeline import part_store
    return part_store.get_categories()


def classify_category(image: Image.Image) -> Optional[str]:
    """调用百炼API判断零件类别，限定为底库已有的类别名称。失败时返回None（触发降级）。"""
    try:
        categories = _get_categories()
        if not categories:
            logger.warning("底库没有类别数据，跳过百炼分类，直接全库检索")
            return None

        categories_str = "、".join(categories)
        prompt = f"请判断这张图片中零件的类别，只返回以下类别之一：{categories_str}。不要返回其他类别名称，不要解释。"
        response = _call_api(image, prompt)
        category = response.choices[0].message.content.strip()
        logger.info(f"百炼API类别判断: {category}, 库中类别: {categories}")
        if category in categories:
            return category
        logger.warning(f"百炼API返回类别'{category}'不在底库中，降级为全库检索")
        return None
    except Exception as e:
        logger.warning(f"百炼API调用失败，将降级为全库检索: {e}")
        return None