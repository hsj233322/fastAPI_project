import os
import logging
import re
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from schemas.ai_assistant import ChatMessage, RelatedJob
from crud.internship import search_internships_by_keyword

logger = logging.getLogger(__name__)


class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = "deepseek-v4-flash"

        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not configured, AI assistant will be disabled")

    async def build_system_prompt(self, db: AsyncSession, user_message: str) -> tuple[str, list[dict[str, str]]]:
        keywords = self._extract_keywords(user_message)
        related_jobs = []

        for keyword in keywords[:5]:
            jobs = await search_internships_by_keyword(db, keyword, limit=3)
            related_jobs.extend(jobs)

        related_jobs = related_jobs[:8]

        job_context = ""
        if related_jobs:
            job_context = "\n\n相关岗位信息（用于回答用户问题时参考）：\n"
            for idx, job in enumerate(related_jobs, 1):
                salary_range = f"{job.salary_min}-{job.salary_max}k" if job.salary_min and job.salary_max else "薪资面议"
                job_context += (
                    f"{idx}. 岗位：{job.title}\n"
                    f"   公司：{job.company_name}\n"
                    f"   薪资：{salary_range}\n"
                    f"   地点：{job.province}\n"
                    f"   学历：{job.education or '不限'}\n\n"
                )

        system_prompt = (
            "你是一个求职实习平台的智能助手，名叫'实习帮助手'。\n"
            "你的任务是帮助用户解答关于实习岗位的问题。\n"
            "\n"
            "请遵循以下规则：\n"
            "1. 始终使用中文回复\n"
            "2. 回答要简洁、专业、友好\n"
            "3. 如果用户的问题涉及具体岗位，优先使用提供的岗位数据进行回答\n"
            "4. 如果没有相关岗位数据，可以基于你的知识回答，但要明确说明这是通用建议\n"
            "5. 可以推荐相关岗位，并说明推荐理由\n"
            "6. 不要编造数据，如果不确定可以说'暂无相关信息'\n"
            "7. 如果用户询问如何使用平台，可以介绍岗位大厅、收藏、浏览历史等功能\n"
            "\n"
            "常见问题示例：\n"
            "- '北京有哪些开发岗位？' -> 列出北京地区的开发相关岗位\n"
            "- '这个岗位薪资多少？' -> 根据岗位数据回答\n"
            "- '如何收藏岗位？' -> 说明收藏功能的使用方法\n"
            "- '简历怎么写？' -> 提供简历撰写建议\n"
            f"{job_context}"
        )

        return system_prompt, related_jobs

    def _extract_keywords(self, text: str) -> list[str]:
        province_keywords = [
            "北京", "上海", "广东", "江苏", "浙江", "四川", "湖北", "湖南", "陕西",
            "山东", "河南", "福建", "安徽", "重庆", "天津", "河北", "辽宁", "黑龙江",
            "江西", "广西", "云南", "山西", "甘肃", "新疆", "宁夏", "西藏", "全国"
        ]
        education_keywords = ["专科", "本科", "硕士", "博士"]
        category_keywords = [
            "开发", "算法", "测试", "产品", "运营", "设计", "市场", "销售",
            "财务", "行政", "法务", "人事", "实习", "工程师", "经理", "助理"
        ]

        keywords = []

        for kw in province_keywords:
            if kw in text:
                keywords.append(kw)

        for kw in education_keywords:
            if kw in text:
                keywords.append(kw)

        for kw in category_keywords:
            if kw in text:
                keywords.append(kw)

        word_pattern = re.compile(r'[\u4e00-\u9fa5]{2,}')
        matched_words = word_pattern.findall(text)
        for word in matched_words:
            if word not in keywords and len(word) >= 2:
                keywords.append(word)

        return keywords[:8]

    async def call_deepseek_api(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str | None:
        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return None

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            return None

    async def chat(
        self,
        db: AsyncSession,
        message: str,
        conversation_history: list[ChatMessage] | None = None,
    ) -> tuple[str, list[RelatedJob]]:
        system_prompt, related_jobs = await self.build_system_prompt(db, message)

        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": message})

        reply = await self.call_deepseek_api(system_prompt, messages)

        if not reply:
            reply = "抱歉，AI助手暂时无法响应，请稍后再试。"

        related_job_schemas = []
        for job in related_jobs:
            related_job_schemas.append(RelatedJob.model_validate(job))

        return reply, related_job_schemas