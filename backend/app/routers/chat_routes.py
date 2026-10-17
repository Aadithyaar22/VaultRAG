from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth
from ..services import rag

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@router.post("")
def chat(body: ChatIn, user=Depends(auth.current_user)):
    return rag.run(user, body.question)
