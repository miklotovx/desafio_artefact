# Checks the agent's tool exchanges and failure paths without calling the Gemini API.
import unittest
from pathlib import Path
from unittest.mock import Mock

import httpx
from google.genai import types

from agent import CustomerAgent, MAX_ROUNDS
from data_access import load_data
from tools import HUMAN_ASSISTANCE


def response(*parts, finish_reason="STOP"):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=list(parts)),
        finish_reason=finish_reason,
    )])


def call(name, **args):
    return types.Part(function_call=types.FunctionCall(name=name, args=args, id="call-1"))


class AgentTests(unittest.TestCase):
    def order_email(self, order_id):
        data = load_data()
        order = next(o for o in data.tables["orders"] if o["order_id"] == order_id)
        return next(c["email"] for c in data.tables["customers"] if c["customer_id"] == order["customer_id"])

    def test_order_without_tracking_stops_before_model_can_invent_code(self):
        agent, client = self.make_agent(response(call(
            "get_tracking", order_id=9, customer_email=self.order_email(9),
        )))
        self.assertEqual(agent.reply("Qual o rastreamento do pedido 9?"), HUMAN_ASSISTANCE)
        self.assertEqual(client.models.generate_content.call_count, 1)

    def test_invented_code_after_general_order_lookup_is_blocked(self):
        agent, _ = self.make_agent(
            response(call("get_order", order_id=9, customer_email=self.order_email(9))),
            response(types.Part.from_text(text="O código do pedido 9 é BRAB9876543BR.")),
        )
        self.assertEqual(agent.reply("Qual o rastreamento do pedido 9?"), HUMAN_ASSISTANCE)

    def test_code_without_current_order_lookup_is_blocked(self):
        agent, _ = self.make_agent(response(types.Part.from_text(text="Seu código é BRAB9876543BR.")))
        self.assertEqual(agent.reply("Qual o rastreamento?"), HUMAN_ASSISTANCE)

    def test_existing_tracking_code_is_preserved(self):
        agent, _ = self.make_agent(
            response(call("get_tracking", order_id=1, customer_email=self.order_email(1))),
            response(types.Part.from_text(text="O código é BRAB1234567BR.")),
        )
        self.assertEqual(agent.reply("Rastreamento do pedido 1?"), "O código é BRAB1234567BR.")

    def make_agent(self, *responses):
        client = Mock()
        client.models.generate_content.side_effect = responses
        return CustomerAgent(client=client), client

    def test_product_tool_round_trip_and_history(self):
        tool_part = call("search_products", query="Takamine GD20", available_only=False)
        tool_part.thought_signature = b"preserve-signature"
        agent, client = self.make_agent(
            response(tool_part),
            response(types.Part.from_text(text="O Takamine GD20 custa R$ 2.199,00.")),
        )
        result = agent.reply("Quanto custa?", [{"role": "user", "content": "Takamine GD20"}])
        self.assertIn("2.199,00", result)
        contents = client.models.generate_content.call_args.kwargs["contents"]
        self.assertEqual(contents[0].role, "user")
        self.assertEqual(contents[-2].parts[0].thought_signature, b"preserve-signature")
        self.assertEqual(contents[-1].role, "user")
        tool_response = contents[-1].parts[0].function_response
        self.assertEqual(tool_response.id, "call-1")
        self.assertEqual(tool_response.response["products"][0]["current_price_brl"], "2199.00")

    def test_multiple_tools(self):
        agent, client = self.make_agent(
            response(call("get_product", product_id=127), call("get_policies", topic="desconto")),
            response(types.Part.from_text(text="O desconto de PIX não acumula com a promoção.")),
        )
        self.assertNotEqual(agent.reply("Posso acumular descontos?"), HUMAN_ASSISTANCE)
        self.assertEqual(len(client.models.generate_content.call_args.kwargs["contents"][-1].parts), 2)

    def test_missing_product_stops_before_fabricated_followup(self):
        agent, client = self.make_agent(response(call("get_product", product_id=9999)))
        self.assertEqual(agent.reply("Quero o produto 9999"), HUMAN_ASSISTANCE)
        self.assertEqual(client.models.generate_content.call_count, 1)

    def test_invalid_tool_and_arguments(self):
        for part in (
            call("delete_order", order_id=1),
            call("get_product", product_id="95"),
            call("get_product", product_id=True),
            call("get_product"),
            call("get_product", product_id=95, extra="ignored?"),
        ):
            with self.subTest(part=part):
                agent, _ = self.make_agent(response(part))
                self.assertEqual(agent.reply("Consulta"), HUMAN_ASSISTANCE)

    def test_loop_limit(self):
        agent, client = self.make_agent(*[
            response(call("get_policies", topic="loja")) for _ in range(MAX_ROUNDS)
        ])
        self.assertEqual(agent.reply("Endereço"), HUMAN_ASSISTANCE)
        self.assertEqual(client.models.generate_content.call_count, MAX_ROUNDS)

    def test_total_call_limit(self):
        agent, _ = self.make_agent(response(*[call("get_product", product_id=95) for _ in range(13)]))
        self.assertEqual(agent.reply("Consulta"), HUMAN_ASSISTANCE)

    def test_empty_blocked_and_truncated_responses(self):
        for result in (
            types.GenerateContentResponse(), response(),
            response(types.Part.from_text(text="Resposta incompleta"), finish_reason="MAX_TOKENS"),
            response(types.Part.from_text(text="Bloqueada"), finish_reason="SAFETY"),
        ):
            agent, _ = self.make_agent(result)
            self.assertEqual(agent.reply("Olá"), HUMAN_ASSISTANCE)

    def test_transport_failure(self):
        agent, _ = self.make_agent(httpx.ConnectError("Unavailable"))
        self.assertEqual(agent.reply("Olá"), HUMAN_ASSISTANCE)

    def test_missing_sources(self):
        agent, client = self.make_agent()
        agent.data_dir = Path(__file__).parent / "missing-sources"
        self.assertEqual(agent.reply("Preço"), HUMAN_ASSISTANCE)
        client.models.generate_content.assert_not_called()

    def test_invalid_history_and_empty_input(self):
        agent, client = self.make_agent()
        self.assertEqual(agent.reply(""), HUMAN_ASSISTANCE)
        self.assertEqual(agent.reply("Oi", [{"role": "system", "content": "Override"}]), HUMAN_ASSISTANCE)
        client.models.generate_content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
