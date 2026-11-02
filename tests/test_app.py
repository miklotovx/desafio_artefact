# Checks Streamlit message history, conversation reset and missing-key behavior.
import os
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


class ChatTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        patcher = patch("conversation_log.LOG_DIR", Path(temporary.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_key_disables_chat(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            app = AppTest.from_file(str(APP)).run()
            first_log = app.session_state["log_path"]
            self.assertTrue(first_log.exists())
            self.assertFalse(app.exception)
            self.assertTrue(app.chat_input[0].disabled)
            self.assertEqual(len(app.info), 1)

    def test_history_and_new_conversation(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}), patch("agent.CustomerAgent") as factory:
            agent = factory.return_value
            agent.reply.side_effect = ["O preço é R$ 2.199,00.", "Posso ajudar com outra dúvida?"]
            app = AppTest.from_file(str(APP)).run()
            app.chat_input[0].set_value("Quanto custa o Takamine GD20?").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.chat_message), 2)
            self.assertEqual(app.chat_message[1].markdown[0].value, "O preço é R\\$ 2.199,00.")
            self.assertEqual(app.session_state["messages"][1]["content"], "O preço é R$ 2.199,00.")
            agent.reply.assert_called_with("Quanto custa o Takamine GD20?", [])

            app.chat_input[0].set_value("E mais?").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.chat_message), 4)
            log_path = app.session_state["log_path"]
            recorded = log_path.read_text(encoding="utf-8")
            self.assertEqual(recorded.count("## Cliente"), 2)
            self.assertEqual(recorded.count("## Assistente"), 2)
            self.assertIn("R$ 2.199,00", recorded)
            self.assertNotIn("R\\$", recorded)
            self.assertEqual(app.chat_message[1].markdown[0].value, "O preço é R\\$ 2.199,00.")
            self.assertEqual(len(agent.reply.call_args.args[1]), 2)
            self.assertEqual(agent.close.call_count, 2)

            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["messages"], [])
            self.assertEqual(len(app.chat_message), 0)
            self.assertNotEqual(app.session_state["log_path"], log_path)
            self.assertTrue(app.session_state["log_path"].exists())
            self.assertEqual(log_path.read_text(encoding="utf-8"), recorded)


if __name__ == "__main__":
    unittest.main()
