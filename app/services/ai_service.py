from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.models.schemas import AIAnswer
from app.prompts.dental_assistant import SYSTEM_PROMPT
from app.services.knowledge_service import KnowledgeService
from app.utils.security import contains_prompt_injection, is_emergency

logger = logging.getLogger(__name__)


FALLBACK = {
    "uk": "На сайті клініки немає точної інформації з цього питання. Я можу передати ваше питання адміністратору. Залиште, будь ласка, номер телефону.",
    "ru": "На сайте клиники нет точной информации по этому вопросу. Я могу передать ваш вопрос администратору. Оставьте, пожалуйста, номер телефона.",
}
EMERGENCY = {
    "uk": "Це може бути невідкладний стан. Негайно зателефонуйте до клініки за номером +38 066 200 05 23 або зверніться до екстреної медичної служби 103. Бот не може оцінити тяжкість стану.",
    "ru": "Это может быть неотложное состояние. Немедленно позвоните в клинику по номеру +38 066 200 05 23 или обратитесь в экстренную медицинскую службу 103. Бот не может оценить тяжесть состояния.",
}
INJECTION_REPLY = {
    "uk": "Я можу допомогти лише з інформацією про клініку AVIDENTIKA та попередньою заявкою на прийом.",
    "ru": "Я могу помочь только с информацией о клинике AVIDENTIKA и предварительной заявкой на приём.",
}


class AIService:
    def __init__(self, client: AsyncOpenAI, model: str, knowledge: KnowledgeService) -> None:
        self.client = client
        self.model = model
        self.knowledge = knowledge

    async def answer(self, question: str, language: str) -> AIAnswer:
        language = language if language in {"uk", "ru"} else "uk"
        if is_emergency(question):
            return AIAnswer(EMERGENCY[language])
        if contains_prompt_injection(question):
            return AIAnswer(INJECTION_REPLY[language])
        chunks = await self.knowledge.search(question)
        if not chunks:
            return AIAnswer(FALLBACK[language])
        context = "\n\n".join(
            f"SOURCE: {chunk.source_url}\nTITLE: {chunk.page_title}\nCONTENT: {chunk.content}" for chunk in chunks
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=450,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"LANGUAGE: {language}\n\nКОНТЕКСТ AVIDENTIKA:\n{context}\n\nПИТАННЯ:\n{question}"},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            if not text:
                return AIAnswer(FALLBACK[language])
            return AIAnswer(text=text, source_url=chunks[0].source_url)
        except Exception:
            logger.exception("OpenAI answer generation failed")
            return AIAnswer(FALLBACK[language])
