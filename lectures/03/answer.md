# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：（TODO：Codespaces で `uv run python -m app.agent "AIE2026の講座で使う「lecNN-start タグ」とは何ですか？"` を実行して記入）
- `--trace` で見えたツール呼び出し（ツール名と引数）：（TODO：`--trace "LoRAとQLoRAの違いは？"` の `[tool call]` 行を記入）
- 1つの質問での LLM 呼び出し回数（`requests`）：（TODO：`[usage]` の `requests` を記入）
- 追加したツールと、docstring に書いた説明：
  - ツール：`make_quiz(lecture: int) -> str`（[app/tools.py](../../app/tools.py)）。指定した回の用語を用語集から 1 つ無作為に選ぶ。返り値は `{"lecture", "term", "question": "「<用語>」の意味は？", "answer": <用語集の定義>}` の JSON。用語のない回を指定すると、用語のある回の一覧を返す
  - docstring：「指定した回（1始まりの整数）の用語集から用語を1つ選び、確認問題と答えを返す。利用者が『第N回の確認問題を出して』『復習のクイズがほしい』のように、理解度を確かめる問題を求めたときに使う。lecture には対象の回の番号を入れる。返り値の answer は、利用者が答えるまで見せずに、ヒントや答え合わせに使う。」
  - 「いつ使うか」は利用者の言い回しの例で示した。「答えをすぐに見せない」は、docstring と `INSTRUCTIONS` の両方に書いた
  - `uv run python -m app.agent --list-tools` で、モデルに見えるツールが 4 個（search_glossary / get_lecture_summary / make_quiz / save_learning_log）になったことを確認した

## 宿題

- 取り組んだレベル：実装
- やったこと：
  - `save_learning_log(topic: str, note: str)` を [app/tools.py](../../app/tools.py) に追加した。`learning_log/YYYY-MM-DD.md` に `## HH:MM <topic>` と本文を追記する（`learning_log/` は `.gitignore` 済み）
  - [app/agent.py](../../app/agent.py) では `requires_approval=True` で登録し、エージェントの `output_type` を `[str, DeferredToolRequests]` にした。モデルがこのツールを呼ぶと、ツールは実行されず、承認待ちの `DeferredToolRequests` が返って実行が止まる
  - `run_with_approval()` を追加した。止まったら、ツール名と引数を表示して `[y/N]` で確認する。その結果を `DeferredToolResults` として `message_history` と一緒に渡し、実行を再開する。`y` 以外の入力は拒否として扱う（既定は「実行しない」）
  - TestModel を使ったテストを追加した（[tests/test_agent.py](../../tests/test_agent.py)、[tests/test_tools.py](../../tests/test_tools.py)）
    - 呼ばれても承認前は実行されず、ファイルが作られない
    - 承認（`y`）すると 1 ファイル作られ、ツールの戻り値が「保存しました」になる
    - 拒否（`n`）するとファイルが作られず、実行は最後まで終わる
    - `make_quiz` が指定した回の用語だけを出し、answer が用語集の定義と一致する
- 結果：`pytest tests/test_agent.py tests/test_tools.py` で 17 件すべて成功（API キーなし）。`tests/test_mcp_server.py` の 2 件は、手元の Windows 環境に `uv` コマンドがなく MCP サーバーを起動できないため失敗する。今回の変更前から同じ状態で、第5回の範囲
- 気づき・疑問：
  - 承認が必要なツールを足すと、既存テストの「ツール呼び出しの数＝戻り値の数」が成り立たなくなった。承認待ちの呼び出しには、承認されるまで戻り値がないため。テストは、承認待ちの件数を足して比べる形に直した。Human-in-the-loop を入れると、エージェントの 1 回の実行が「止まって、人が答えて、再開する」2 段階になる。呼び出し側のコードもテストもそれを前提に書く必要がある
  - 承認するかどうかはプログラム側（`requires_approval`）で決まり、モデルの判断には任せない。docstring の「明示的に頼んだときだけ使う」はモデルへのお願いにすぎない。書き込みを確実に止めるのは承認の仕組みのほう、という役割分担になっている
  - 疑問：再開時に `message_history` を渡すため、承認 1 回につき LLM 呼び出しが少なくとも 1 回増える。レート制限の厳しい無料枠では、承認待ちの多いツール設計はコストが大きいのではないか
