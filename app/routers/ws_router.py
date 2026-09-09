from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.websocket_manager import manager, authenticate_ws_token, get_company_id_for_user

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query("")):
    if not token:
        await websocket.close(code=4001, reason="Token obrigatorio")
        return

    user_id = authenticate_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Token invalido")
        return

    company_id = get_company_id_for_user(user_id)
    if not company_id:
        await websocket.close(code=4001, reason="Empresa nao encontrada")
        return

    await manager.connect(websocket, company_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket, company_id)
