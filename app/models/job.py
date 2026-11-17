from typing import Literal

from pydantic import BaseModel


class ClipCandidate(BaseModel):
    start: float
    end: float
    title: str
    hook: str
    score: int
    reason: str
    emotion: Literal["funny", "intense", "shocking", "relatable", "inspiring", "interesting"]


class ClipJobResult(BaseModel):
    clips_found: int
    clips_sent: int
