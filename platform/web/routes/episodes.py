"""Episode Manager API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class EpisodeCreate(BaseModel):
    title: str = ""
    prompt: str
    source: str = "user"


class EpisodeResponse(BaseModel):
    episode_id: str
    title: str
    prompt: str
    source: str
    current_stage: str
    created_at: str


@router.get("/")
async def list_episodes():
    """List all episodes."""
    from platform.services.content_factory import ContentFactory
    factory = ContentFactory()
    episodes = factory.list_episodes()
    return [
        EpisodeResponse(
            episode_id=ep.episode_id,
            title=ep.title,
            prompt=ep.prompt,
            source=ep.source,
            current_stage=ep.current_stage.value,
            created_at=ep.created_at.isoformat(),
        )
        for ep in episodes
    ]


@router.post("/", status_code=201)
async def create_episode(body: EpisodeCreate):
    """Create a new episode and start the content pipeline."""
    from platform.services.content_factory import ContentFactory
    factory = ContentFactory()
    episode = await factory.create_episode(
        prompt=body.prompt,
        title=body.title,
        source=body.source,
    )
    return EpisodeResponse(
        episode_id=episode.episode_id,
        title=episode.title,
        prompt=episode.prompt,
        source=episode.source,
        current_stage=episode.current_stage.value,
        created_at=episode.created_at.isoformat(),
    )


@router.get("/{episode_id}")
async def get_episode(episode_id: str):
    """Get episode details."""
    from platform.services.content_factory import ContentFactory
    factory = ContentFactory()
    episode = factory.get_episode(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return EpisodeResponse(
        episode_id=episode.episode_id,
        title=episode.title,
        prompt=episode.prompt,
        source=episode.source,
        current_stage=episode.current_stage.value,
        created_at=episode.created_at.isoformat(),
    )
