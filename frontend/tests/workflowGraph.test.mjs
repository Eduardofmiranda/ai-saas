import assert from "node:assert/strict";
import test from "node:test";
import { connectionIssue, nodeData, suggestedPrompt } from "../src/workflowGraph.js";

const trigger = { id: "trigger", data: nodeData({ input_handles: [], output_handles: ["out"] }) };
const ai = { id: "ai", data: nodeData({ input_handles: ["in"], output_handles: ["out", "error"] }) };
const send = { id: "send", data: nodeData({ input_handles: ["in"], output_handles: ["out", "error"] }) };

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
