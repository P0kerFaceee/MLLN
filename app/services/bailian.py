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


def _call_api(image: Image.Image) -> object:
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
                    {"type": "text", "text": "请判断这张图片中零件的类别，只返回类别名称，不要解释。"},
                ],
            }
        ],
    )
    return response


def classify_category(image: Image.Image) -> str | None:
    """调用百炼API判断零件类别。失败时返回None（触发降级）。"""
    try:
        response = _call_api(image)
        category = response.choices[0].message.content.strip()
        logger.info(f"百炼API类别判断: {category}")
        return category
    except Exception as e:
        logger.warning(f"百炼API调用失败，将降级为全库检索: {e}")
        return None