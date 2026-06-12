"""Character Manager API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory character store (will be replaced with DB later)
_characters: dict[str, dict] = {}


class CharacterCreate(BaseModel):
    name: str
    description: str = ""
    style: str = ""  # visual style description
    voice_id: str = ""  # TTS voice identifier
    model_path: str = ""  # path to 3D model/asset


class CharacterResponse(BaseModel):
    character_id: str
    name: str
    description: str
    style: str
    voice_id: str
    model_path: str


@router.get("/")
async def list_characters():
    """List all characters."""
    return list(_characters.values())


@router.post("/", status_code=201)
async def create_character(body: CharacterCreate):
    """Create a new character."""
    import uuid
    char_id = str(uuid.uuid4())[:8]
    character = {
        "character_id": char_id,
        "name": body.name,
        "description": body.description,
        "style": body.style,
        "voice_id": body.voice_id,
        "model_path": body.model_path,
    }
    _characters[char_id] = character
    return character


@router.get("/{character_id}")
async def get_character(character_id: str):
    """Get character details."""
    if character_id not in _characters:
        raise HTTPException(status_code=404, detail="Character not found")
    return _characters[character_id]


@router.delete("/{character_id}")
async def delete_character(character_id: str):
    """Delete a character."""
    if character_id not in _characters:
        raise HTTPException(status_code=404, detail="Character not found")
    del _characters[character_id]
    return {"status": "deleted"}
