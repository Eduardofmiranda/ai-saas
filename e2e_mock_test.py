"""Teste ponta a ponta (E2E) via API + Mock Evolution.

Roda todo o fluxo SEM WhatsApp real nem Evolution real:
  1. Cria conta (register)  ->  retorna company_id e token
  2. Configura a IA como "mock" (nao gasta tokens) e aponta a Evolution para o mock
  3. Usa o template "Atendimento Basico" (ou cria workflow manual)
  4. Ativa o workflow
  5. Simula o cliente enviando "ola"  ->  dispara o webhook do backend
  6. Aguarda e verifica a resposta capturada no mock

Pre-requisitos (3 terminais ou suba antes):
  Term A:  python mock_evolution_server.py
  Term B:  (backend apontando pro mock)
           $env:EVOLUTION_BASE_URL="http://localhost:8090"
           $env:EVOLUTION_API_KEY="mock" ; $env:EVOLUTION_INSTANCE="flowai"
           uvicorn app.main:app --port 8000

Uso:
  python e2e_mock_test.py

Quando terminar: veja a lista de mensagens enviadas no mock em
  GET http://localhost:8090/sent_messages
"""
from __future__ import annotations

import time

import httpx

BACKEND = "http://localhost:8000"
MOCK = "http://localhost:8090"
EMAIL = "e2e@test.com"


def fmt(x):
    import json
    return json.dumps(x, indent=2, ensure_ascii=False)


def main() -> None:
    with httpx.Client(timeout=30) as c:
        # 1. Registro (idempotente: se email ja existe, faz login)
        reg = c.post(f"{BACKEND}/auth/register",
                     json={"company_name": "Empresa E2E", "name": "E2E",
                           "email": EMAIL, "password": "senha123"})
        if reg.status_code == 409:
            token = c.post(f"{BACKEND}/auth/login",
                           data={"username": EMAIL, "password": "senha123"}).json()["access_token"]
            company_id = c.post(f"{BACKEND}/auth/login",
                                data={"username": EMAIL, "password": "senha123"}).json()["company_id"]
        else:
            body = reg.json()
            token = body["access_token"]
            company_id = body["company_id"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[1] company_id={company_id} token ok")

        # 2. Configuracao: IA mock + Evolution apontando pro mock
        r = c.patch(f"{BACKEND}/config/", json={
            "ai_provider": "mock",
            "ai_model": "mock-model",
            "ai_api_key": "mock",
            "ai_base_url": "http://mock",
            "evolution_base_url": MOCK,
            "evolution_api_key": "mock",
            "evolution_instance": "flowai",
            "ai_on": True,
        }, headers=headers)
        print(f"[2] config patch -> {r.status_code}")

        # 3. Usar template "Atendimento Basico"
        tpl = c.get(f"{BACKEND}/templates/", headers=headers).json()
        atendimento = next((t for t in tpl if t["id"] == "atendimento_basico"), tpl[0])
        r = c.post(f"{BACKEND}/templates/{atendimento['id']}/use", headers=headers)
        print(f"[3] use template -> {r.status_code}")
        wf = r.json()
        wf_id = wf["id"] if isinstance(wf, dict) else None

        # Se o template "use" nao retorna o workflow, busca a lista
        if wf_id is None:
            wfs = c.get(f"{BACKEND}/workflows/", headers=headers).json()
            wf_id = wfs[0]["id"]
        print(f"    workflow_id={wf_id}")

        # 4. Ativar este workflow (e desativar outros ativos, para evitar ambiguidade)
        other_wfs = c.get(f"{BACKEND}/workflows/", headers=headers).json()
        for other in other_wfs:
            if other.get("id") != wf_id and other.get("active"):
                c.patch(f"{BACKEND}/workflows/{other['id']}", json={"active": False}, headers=headers)
        c.patch(f"{BACKEND}/workflows/{wf_id}", json={"active": True}, headers=headers)
        print("[4] workflow ativo")

        # 5. Simular cliente enviando mensagem
        sim = c.post(f"{MOCK}/simulate_message", json={
            "company_id": company_id,
            "phone": "5511999999999",
            "text": "ola, preciso de ajuda",
        })
        print(f"[5] simulate -> {sim.status_code}")
        print("    resposta do backend:", sim.text)

        # 6. Aguardar processamento async e checar envio capturado no mock
        print("[6] aguardando processamento...")
        time.sleep(3)
        sent = c.get(f"{MOCK}/sent_messages").json()
        print("    mensagens enviadas (pelo backend -> mock):")
        print(fmt(sent))

        if sent.get("count", 0) > 0:
            print("\n>>> E2E OK - resposta enviada foi capturada pelo mock!")
            print(">>> Abra http://localhost:8090/sent_messages no navegador para inspecionar.")
        else:
            print("\n>>> Nenhuma mensagem enviada ainda. Veja spoilers em:")
            print("    GET http://localhost:8090/sent_messages")
            print("    GET http://localhost:8090/received_webhooks")
            print("    e os logs do backend (uvicorn).")


if __name__ == "__main__":
    main()
