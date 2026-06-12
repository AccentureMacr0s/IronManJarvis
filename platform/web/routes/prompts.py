"""Prompt Library API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# In-memory prompt store
_prompts: dict[str, dict] = {}


class PromptCreate(BaseModel):
    name: str
    template: str
    category: str = "general"  # general | scenario | storyboard | voice
    variables: list[str] = []


class PromptResponse(BaseModel):
    prompt_id: str
    name: str
    template: str
    category: str
    variables: list[str]
    created_at: str


@router.get("/")
async def list_prompts(category: str | None = None):
    """List all prompts, optionally filtered by category."""
    prompts = list(_prompts.values())
    if category:
        prompts = [p for p in prompts if p["category"] == category]
    return prompts


@router.post("/", status_code=201)
async def create_prompt(body: PromptCreate):
    """Create a new prompt template."""
    import uuid
    prompt_id = str(uuid.uuid4())[:8]
    prompt = {
        "prompt_id": prompt_id,
        "name": body.name,
        "template": body.template,
        "category": body.category,
        "variables": body.variables,
        "created_at": datetime.utcnow().isoformat(),
    }
    _prompts[prompt_id] = prompt
    return prompt


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get prompt details."""
    if prompt_id not in _prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _prompts[prompt_id]


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt."""
    if prompt_id not in _prompts:
        raise HTTPException(status_code=404, detail="Prompt not found")
    del _prompts[prompt_id]
    return {"status": "deleted"}
