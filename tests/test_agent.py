"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent, run_with_approval

BASE_TOOLS = {"search_glossary", "get_lecture_summary"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    model = TestModel()
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    # 承認が必要なツール（save_learning_log）は、承認されるまで実行されず戻り値がない
    pending = len(result.output.approvals) if isinstance(result.output, DeferredToolRequests) else 0
    assert len(_parts(result, ToolReturnPart)) + pending == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"


def test_make_quiz_is_registered_and_returns_quiz():
    model = TestModel(call_tools=["make_quiz"])
    with agent.override(model=model):
        result = agent.run_sync("第2回の確認問題を出して")
    returns = _parts(result, ToolReturnPart)
    assert [r.tool_name for r in returns] == ["make_quiz"]


def test_save_learning_log_waits_for_approval(tmp_path, monkeypatch):
    """承認が必要なツールは、呼ばれても実行されずに止まる（ファイルは作られない）。"""
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = agent.run_sync("今日の学びを記録して")
    assert isinstance(result.output, DeferredToolRequests)
    assert [c.tool_name for c in result.output.approvals] == ["save_learning_log"]
    assert not (tmp_path / "learning_log").exists()


def test_save_learning_log_runs_only_when_approved(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    answers = iter(["y"])
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = run_with_approval(agent, "今日の学びを記録して", model, confirm=lambda _: next(answers))
    assert isinstance(result.output, str)
    logs = list((tmp_path / "learning_log").glob("*.md"))
    assert len(logs) == 1
    returns = [r for r in _parts(result, ToolReturnPart) if r.tool_name == "save_learning_log"]
    assert "保存しました" in returns[0].content


def test_save_learning_log_is_skipped_when_denied(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = run_with_approval(agent, "今日の学びを記録して", model, confirm=lambda _: "n")
    assert isinstance(result.output, str)
    assert not (tmp_path / "learning_log").exists()
