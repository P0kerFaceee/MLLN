import io
import logging
import base64
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


def _call_api(image: Image.Image, prompt: str) -> object:
    """调用百炼多模态API，返回原始响应对象。"""
    client = _get_client()
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

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


def _get_categories() -> list[str]:
    """延迟获取底库类别列表，避免循环导入。"""
    from app.services.pipeline import vector_store
    return vector_store.get_categories()


def classify_category(image: Image.Image) -> str | None:
    """调用百炼API判断零件类别，限定为底库已有的类别名称。失败时返回None（触发降级）。"""
    try:
        categories = _get_categories()
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