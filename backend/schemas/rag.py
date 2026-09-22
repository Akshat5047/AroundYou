from pydantic import BaseModel


class RAGQuestion(BaseModel):
    question: str
    top_k: int = 3