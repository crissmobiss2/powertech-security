from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, clients, sites, assets, incidents, alerts, tickets, playbooks,
    events, users, vision, ws, threat_response, biometrics, ai_stream,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(users.router, prefix="/users", tags=["Users"])
api_v1_router.include_router(clients.router, prefix="/clients", tags=["Clients"])
api_v1_router.include_router(sites.router, prefix="/sites", tags=["Sites"])
api_v1_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_v1_router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
api_v1_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_v1_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
api_v1_router.include_router(playbooks.router, prefix="/playbooks", tags=["Automation Playbooks"])
api_v1_router.include_router(events.router, prefix="/events", tags=["Security Events"])
api_v1_router.include_router(vision.router, prefix="/vision", tags=["AI Vision"])
api_v1_router.include_router(biometrics.router, prefix="/biometrics", tags=["Biometrics"])
api_v1_router.include_router(ai_stream.router, prefix="/ai-stream", tags=["AI Stream & LiveKit"])
api_v1_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])
api_v1_router.include_router(threat_response.router, prefix="/threat-response", tags=["Threat Response"])
