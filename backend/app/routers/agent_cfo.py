import logging

from fastapi import APIRouter, HTTPException, Request

from app.schemas.agent_cfo import AgentCFORequest, AgentCFOResponse
from app.services.agent_cfo_service import AgentCFOServiceError, answer_question


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent_cfo", tags=["agent_cfo"])


@router.post("", response_model=AgentCFOResponse)
async def ask_agent_cfo(
    request: Request,
    body: AgentCFORequest,
) -> AgentCFOResponse:
    client_ip = request.client.host if request.client else None
    try:
        return await answer_question(body.question, client_ip)
    except AgentCFOServiceError as error:
        logger.exception("Agent CFO request failed")
        raise HTTPException(
            status_code=502,
            detail="The CFO agent could not complete the request",
        ) from error
