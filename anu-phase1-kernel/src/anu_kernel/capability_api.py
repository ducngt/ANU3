from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .api_dependencies import get_session
from .capability_contracts import CapabilityContract, CapabilityDiscoveryQuery, SmartBoxManifest
from .capability_repository import add_capability, add_smart_box
from .capability_services import discover_capabilities

router = APIRouter(prefix="/v3", tags=["Phase 3 Capability Contract/Registry"])


@router.post("/capabilities")
def create_capability(body: CapabilityContract, session: Session = Depends(get_session)):
    add_capability(session, body)
    return body


@router.post("/boxes")
def create_smart_box(body: SmartBoxManifest, session: Session = Depends(get_session)):
    add_smart_box(session, body)
    return body


@router.post("/discover")
def discover(body: CapabilityDiscoveryQuery, session: Session = Depends(get_session)):
    return discover_capabilities(session, body)
