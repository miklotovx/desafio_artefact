# Displays the Streamlit chat and keeps customer messages in the current session.
"""Local PT-BR interface for the Empório da Música customer-service agent."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent import ConfigurationError, CustomerAgent
from conversation_log import new_log_path, save_log


def render_message(text: str) -> None:
    """Escape currency dollars for display, keeping the original session text."""
    st.markdown(text.replace("R$", "R\\$"))


def save_conversation() -> None:
    """Keep the chat usable if the local log cannot be written."""
    try:
        save_log(st.session_state.log_path, st.session_state.messages)
    except OSError:
        st.warning("Não foi possível salvar o registro desta conversa na pasta logs.")


st.set_page_config(page_title="Empório da Música", page_icon="🎵", layout="centered")
load_dotenv(Path(__file__).resolve().parent / ".env")

st.title("Empório da Música")
st.caption("Sua música começa aqui. Como podemos ajudar?")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "log_path" not in st.session_state:
    st.session_state.log_path = new_log_path()
    save_conversation()

if st.button("Nova conversa"):
    st.session_state.messages = []
    st.session_state.log_path = new_log_path()
    save_conversation()
    st.rerun()

configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
if not configured:
    st.info("Para iniciar o chat, configure GEMINI_API_KEY no arquivo .env do projeto.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        render_message(message["content"])

prompt = st.chat_input("Digite sua mensagem", disabled=not configured)
if prompt and prompt.strip():
    history = [message.copy() for message in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_conversation()
    with st.chat_message("user"):
        render_message(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando..."):
            try:
                agent = CustomerAgent()
            except ConfigurationError as exc:
                st.error(str(exc))
                st.session_state.messages.pop()
                save_conversation()
                st.stop()
            try:
                answer = agent.reply(prompt, history)
            finally:
                agent.close()
        render_message(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_conversation()
