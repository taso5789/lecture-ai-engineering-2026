"""APIを呼ばずに、第1回の使用量表示と会話の継続を検証する。"""

from unittest.mock import MagicMock

import pytest
from google.genai import errors, types

from app import ask


@pytest.fixture
def client(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(ask, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask.genai, "Client", MagicMock(return_value=mock))
    return mock.__enter__.return_value


def response(text="回答"):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text=text)]
        ))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=12, candidates_token_count=0
        ),
    )


def test_ask_returns_text_and_prints_usage(client, capsys):
    client.models.generate_content.return_value = response()
    assert ask.ask("LoRAとは？") == "回答"
    client.models.generate_content.assert_called_once_with(
        model=ask.MODEL, contents="LoRAとは？"
    )
    assert "入力: 12 / 出力: 0" in capsys.readouterr().out


def test_missing_usage(capsys):
    ask.print_usage(types.GenerateContentResponse())
    assert "入力: 不明 / 出力: 不明" in capsys.readouterr().out


def test_chat_reuses_session_and_ignores_blank_input(client, monkeypatch):
    session = client.chats.create.return_value
    session.send_message.return_value = response()
    inputs = iter(["  ", "具体例は？", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    ask.chat("LoRAとは？")
    client.chats.create.assert_called_once_with(model=ask.MODEL)
    assert [call.args[0] for call in session.send_message.call_args_list] == [
        "LoRAとは？", "具体例は？"
    ]


@pytest.mark.parametrize("interrupt", [EOFError, KeyboardInterrupt])
def test_chat_ends_on_terminal_interrupt(client, monkeypatch, interrupt):
    client.chats.create.return_value.send_message.return_value = response()

    def stop(_):
        raise interrupt

    monkeypatch.setattr("builtins.input", stop)
    ask.chat("質問")


def test_chat_continues_after_api_error(client, monkeypatch, capsys):
    session = client.chats.create.return_value
    session.send_message.side_effect = [
        errors.APIError(429, {"error": {"message": "quota exceeded"}}),
        response("再試行の回答"),
    ]
    inputs = iter(["もう一度", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    ask.chat("質問")
    out = capsys.readouterr().out
    assert "レート制限に達しました" in out
    assert "再試行の回答" in out
    assert [call.args[0] for call in session.send_message.call_args_list] == [
        "質問", "もう一度"
    ]


def test_main_reports_api_error(client, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["ask", "質問"])
    client.models.generate_content.side_effect = errors.APIError(
        429, {"error": {"message": "quota exceeded"}}
    )
    with pytest.raises(SystemExit, match="1"):
        ask.main()
    assert "レート制限に達しました" in capsys.readouterr().out
