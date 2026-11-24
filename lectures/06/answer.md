# 第6回 解答

## 演習

<!-- [tool call] の行は、表示された行をそのまま貼り付けてください。終わらなかった STEP は、空欄のままでかまいません。 -->

- STEP 1 のツールの名前：glossary_search_glossary
- STEP 2 の [tool call]：`glossary_search_glossary({'query': '3レベル'})`
- STEP 3 の [tool call]：
  - 1 回目：`fetch_fetch({'url': 'https://modelcontextprotocol.io/'})` → `[tool error]` 30000 ms でタイムアウト
  - 2 回目：`fetch_fetch({'timeout_ms': 60000, 'url': 'https://modelcontextprotocol.io/'})` → 取得成功
- STEP 4 の [tool call]：`aws_aws___search_documentation({'topics': ['general'], 'search_phrase': 'Amazon S3 Versioning overview'})`
- 気づき・疑問：
  - STEP 2 は `[usage]` が「モデル応答 2 回」。1 回目でツールを呼び、2 回目で用語集の結果を読んで「基礎・実装・発展」の 3 段階と答えた。第3回と同じ答えで、関数を呼ぶのがエージェントから MCP サーバーに変わっただけだった
  - STEP 3 では、1 回目の fetch がタイムアウトした。`[tool error]` の内容がモデルに渡り、モデルは引数 `timeout_ms` を 60000 に増やして自分で呼び直した（モデル応答 3 回）。エラーの文面とツールの引数の説明が、モデルの立て直しに使われている
  - fetch はページを取得する前に `robots.txt` を取りに行っていた。README の「robots.txt で禁止されたページは取得しない」という既定の動作を、ログで確かめられた
  - STEP 4 で `aws` を足すと、ツールが 2 個から 7 個に増えた（`aws_aws___search_documentation`・`read_documentation`・`list_regions`・`get_regional_availability`・`retrieve_skill`）。名前が `aws_aws___…` と二重になるのは、サーバー側のツール名がもともと `aws___` で始まり、その前に設定ファイルのサーバー名 `aws_` が付くため
  - ツールが増えると、質問と関係のないツールの説明文も毎回モデルに渡る。STEP 4 の入力は 6,523 tokens で、STEP 2（715 tokens）より大きく増えた（検索結果の本文の分もある）
  - Windows の手元環境では、`uv` が PATH にないと glossary サーバーを起動できず、「MCP サーバーに接続できませんでした: [WinError 2]」と出た。`"command"` の起動は、エージェントを動かす環境の PATH に依存する
  - STEP 3・4 では、Gemini の 503（混雑）が何度か出た。待って再実行した結果を記録した

## 宿題

<!-- 基礎・実装・発展のどれか1つに取り組めば完了です。 -->

- 取り組んだレベル：基礎
- やったこと：`app/mcp_server.py` の `TODO` の下に `server.tool()(tools.get_lecture_summary)` の 1 行を書き足した。エージェント側の `app/mcp_servers.json` と `app/mcp_agent.py` は変えていない（`git status` で変更が `app/mcp_server.py` だけであることを確認した）
- 結果：
  - `--list-tools` で、ツールが 7 個から 8 個に増え、`glossary_get_lecture_summary`（引数 `{"lecture": {"title": "Lecture", "type": "integer"}}`）が表示された
  - 「第2回では何を学びますか？」の `[tool call]`：`glossary_get_lecture_summary({'lecture': 2})`。用語集の検索ではなく、追加したツールが 1 回で選ばれた。回答は「ファインチューニングとLoRA」で、事前学習との違い・SFT・PEFT と LoRA・Colab での演習を挙げた（入力 5,942 tokens / 出力 291 tokens / モデル応答 2 回）
  - `uv run pytest -q`：21 passed
- 気づき・疑問：
  - エージェントは起動のたびにサーバーへツールの一覧を問い合わせるので、サーバー側に 1 行足すだけで、エージェントを変えずに新しいツールが使えた
  - モデルが 2 つの glossary のツールを使い分けられたのは、docstring に「『第3回では何を学ぶ？』のように、回の内容を聞かれたときに使う」と使う場面が書いてあるからだと思う。説明文がそのままモデルへの指示になる
  - 引数が `integer` と型で示されるので、モデルは「第2回」を `2` に変換して渡した。範囲外の回（例：第99回）を渡したときにどう返るかは、実装レベルで確かめたい
