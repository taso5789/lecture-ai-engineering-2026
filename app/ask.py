"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --chat "LoRAとは何ですか？"

ツールを持たない「素の」呼び出し。--chat では終了まで会話履歴を保持する。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors, types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def print_usage(response: types.GenerateContentResponse) -> None:
    """APIが使用量を返さなかった場合は、0と区別して表示する。"""
    usage = response.usage_metadata
    prompt = usage.prompt_token_count if usage else None
    candidates = usage.candidates_token_count if usage else None
    print(
        f"[トークン] 入力: {prompt if prompt is not None else '不明'} / "
        f"出力: {candidates if candidates is not None else '不明'}"
    )


def ask(question: str) -> str:
    with genai.Client(api_key=get_api_key()) as client:
        response = client.models.generate_content(model=MODEL, contents=question)
        print_usage(response)
        return response.text or "（テキストの回答がありません）"


def chat(question: str) -> None:
    """同じチャットに質問を送り、ユーザーとモデルの発言を保持する。"""
    with genai.Client(api_key=get_api_key()) as client:
        session = client.chats.create(model=MODEL)
        print("続けて質問できます。/exit または /quit で終了します。")
        while True:
            try:
                response = session.send_message(question)
            except errors.APIError as e:
                # 失敗しても会話は終えず、次の質問を受け付ける（失敗した質問は履歴に残らない）
                print(api_error_message(e.code, e.message))
            else:
                print_usage(response)
                print(response.text or "（テキストの回答がありません）")
            while True:
                try:
                    question = input("\n[質問] ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                if question in {"/exit", "/quit"}:
                    return
                if question:
                    break


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--chat", action="store_true", help="会話履歴を保って続けて質問する")
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    print(f"[質問] {args.question}\n")
    try:
        if args.chat:
            chat(args.question)
        else:
            print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
