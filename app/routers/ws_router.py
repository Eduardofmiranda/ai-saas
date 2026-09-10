from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager, authenticate_ws_token, get_company_id_for_user

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    protocols = [value.strip() for value in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    protocol_token = protocols[1] if len(protocols) >= 2 and protocols[0] == "access-token" else ""
    # Query string permanece como compatibilidade temporaria para clientes
    # antigos; o frontend atual envia o JWT no handshake, fora da URL.
    token = protocol_token or websocket.query_params.get("token", "")
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

    await manager.connect(
        websocket,
        company_id,
        user_id,
        subprotocol="access-token" if protocol_token else None,
    )
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, company_id)
