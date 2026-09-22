from fastapi import APIRouter, HTTPException

from schemas.rag import RAGQuestion
from services.rag_service import answer_question


router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"]
)


@router.post("/ask")
def ask_rag(request: RAGQuestion):

    try:
        return answer_question(
            question=request.question,
            top_k=request.top_k
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )