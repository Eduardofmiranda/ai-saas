import assert from "node:assert/strict";
import test from "node:test";
import { activationChecklist, connectionIssue, integrationChecklist, nodeData, suggestedPrompt, workflowGuidance } from "../src/workflowGraph.js";

const trigger = { id: "trigger", type: "trigger_message", data: nodeData({ input_handles: [], output_handles: ["out"] }) };
const ai = { id: "ai", type: "ai", data: nodeData({ input_handles: ["in"], output_handles: ["out", "error"] }) };
const send = { id: "send", type: "whatsapp_send", data: nodeData({ input_handles: ["in"], output_handles: ["out", "error"] }) };

test("aceita uma conexao valida", () => {
  assert.equal(connectionIssue({ source: "trigger", target: "ai", sourceHandle: "out" }, [trigger, ai], []), "");
});

test("rejeita conexao para trigger, duplicada e ciclica", () => {
  assert.match(connectionIssue({ source: "ai", target: "trigger", sourceHandle: "out" }, [trigger, ai], []), /trigger/);
  const edges = [{ source: "trigger", target: "ai", sourceHandle: "out" }, { source: "ai", target: "send", sourceHandle: "out" }];
  assert.match(connectionIssue({ source: "trigger", target: "ai", sourceHandle: "out" }, [trigger, ai, send], edges), /ja existe/);
  assert.match(connectionIssue({ source: "send", target: "trigger", sourceHandle: "out" }, [trigger, ai, send], edges), /trigger/);
  assert.match(connectionIssue({ source: "send", target: "ai", sourceHandle: "out" }, [trigger, ai, send], edges), /ciclo/);
});

test("mantem os handles vindos do contrato do backend", () => {
  const data = nodeData({ label: "Condicao", input_handles: ["in"], output_handles: ["true", "false", "error"] });
  assert.deepEqual(data.input_handles, ["in"]);
  assert.deepEqual(data.output_handles, ["true", "false", "error"]);
});
test("oferece prompts seguros para IA e RAG", () => {
  assert.match(suggestedPrompt("ai"), /data\.message\.text/);
  assert.equal(suggestedPrompt("ai_rag"), "{{ data.message.text }}");
  assert.equal(suggestedPrompt("log"), "");
});
test("orienta quando a resposta de IA nao chega ao WhatsApp", () => {
  const advice = workflowGuidance([trigger, ai], [{ source: "trigger", target: "ai" }]);
  assert.equal(advice?.sourceNodeId, "ai");
  assert.match(advice?.message || "", /Enviar WhatsApp/);
});

test("nao orienta quando o envio de WhatsApp e alcancavel", () => {
  const advice = workflowGuidance(
    [trigger, ai, send],
    [{ source: "trigger", target: "ai" }, { source: "ai", target: "send" }],
  );
  assert.equal(advice, null);
});
test("checklist separa pendencias do canvas de verificacoes externas", () => {
  const incomplete = activationChecklist([trigger, ai], [{ source: "trigger", target: "ai" }]);
  assert.equal(incomplete.find((item) => item.id === "message-trigger")?.state, "ready");
  assert.equal(incomplete.find((item) => item.id === "response-delivery")?.state, "warning");
  assert.equal(incomplete.find((item) => item.id === "whatsapp-fields")?.state, "not_applicable");

  const configuredAi = {
    ...ai,
    data: { ...ai.data, prompt: "{{ data.message.text }}" },
  };
  const configuredSend = {
    ...send,
    data: { ...send.data, phone: "{{ data.phone }}", text: "{{ data.ai_reply }}" },
  };
  const complete = activationChecklist(
    [trigger, configuredAi, configuredSend],
    [{ source: "trigger", target: "ai" }, { source: "ai", target: "send", sourceHandle: "out" }],
  );
  assert.equal(complete.every((item) => item.state !== "warning"), true);
});

test("mostra o resultado real das conexoes sem confundir com o canvas", () => {
  const ready = integrationChecklist(
    { ok: true, detail: "IA respondeu via openai com gpt-test." },
    { state: "open", instance: "inst-3" },
  );
  assert.equal(ready.every((item) => item.state === "ready"), true);
  assert.match(ready.find((item) => item.id === "whatsapp-connection")?.detail || "", /inst-3/);

  const warning = integrationChecklist(
    { ok: false, detail: "Provedor retornou HTTP 429" },
    { state: "close", detail: "WhatsApp desconectado" },
  );
  assert.equal(warning.every((item) => item.state === "warning"), true);
  assert.match(warning.find((item) => item.id === "ai-connection")?.detail || "", /429/);
});
