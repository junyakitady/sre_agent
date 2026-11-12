# GCP SRE Agent (sre_agent)

このプロジェクトは、Gemini Enterprise Agent Runtime (旧 Vertex AI Agent Engine / Reasoning Engine) 上に構築およびデプロイ可能な、Google Cloud のインフラ監視・トラブルシューティング支援のための SRE AI エージェントです。

## 主な機能

* **GCP ログ調査と段階的トリアージ**: [Google Cloud Logging MCP](https://logging.googleapis.com) と統合し、特定の GCP プロジェクトからエラーログや警告ログを高度にフィルタ・検索できます。Context Bloat（コンテキスト肥大化）を防ぐため、`pageSize=20` 以下・`orderBy="timestamp desc"`・具体的な `filter` を用いて段階的に調査します。
* **技術情報の提供と根拠ある分析**: [Google Developer Knowledge MCP](https://developerknowledge.googleapis.com) と統合し、Google Cloud や関連開発者製品の公式ドキュメント、ベストプラクティスに基づいた正確な技術情報を提供し、情報源の公式 URL を引用します。
* **止血優先とリスク評価付き構造化報告**: Google SRE ベストプラクティスに基づき、コマンド提示時にはリスク評価ブロック（`⚪ NONE | 🟢 LOW | 🟡 MEDIUM | 🔴 HIGH`）を付与し、事象サマリー・根拠・根本原因仮説（確信度付き）・推奨アクション（緩和策/恒久対策）の4部構成で報告します。
* **高度な認証制御**: Application Default Credentials (ADC) を用いて認証トークンを動的に取得・キャッシュし、有効期限が切れた場合のみ自動でリフレッシュします。また、必要な `X-Goog-User-Project` ヘッダーを適切にインジェクトします。
* **リトライ制御とエラー回復**: `Gemini` モデルの `HttpRetryOptions` による LLM API リトライおよび ADK の `ReflectAndRetryToolPlugin` によるツール実行失敗時の自動再試行を備えています。
* **イベント履歴の自動圧縮 (Compaction)**: `EventsCompactionConfig` により、長期セッションや大量ログ調査時のコンテキストウィンドウ肥大化を自動で要約・圧縮します（トークンベース圧縮: `token_threshold=200000`, `event_retention_size=2`、要約モデル: `LlmEventSummarizer` で `gemini-3.8-flash` を使用）。
* **テレメトリとトレース制御**: OpenTelemetry による Cloud Trace 連携（`GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY='true'`）を有効化しつつ、大容量プロンプトによる Cloud Logging 書き出し上限超過を防ぐため、プロンプト・レスポンス本文の記録を無効化（`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='NO_CONTENT'`, `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'`）しています。

## プロジェクト構成

```text
sre_agent/
├── README.md                          # 本ドキュメント
├── requirements.txt                   # プロジェクト共通の依存関係
└── sre_agent/
    ├── __init__.py                    # パッケージ初期化
    ├── agent.py                       # エージェント定義および認証ロジック
    ├── SA_agent_engine_config.json    # サービスアカウント認証用のデプロイ構成
    ├── ID_agent_engine_config.json    # Agent Identity 用のデプロイ構成
    ├── .env                           # ローカル開発用の環境変数設定
    └── requirements.txt               # ランタイム用の依存関係
```

## 必要条件

### GCP API の有効化
以下の API がデプロイ先および実行先の GCP プロジェクトで有効化されている必要があります。
* `aiplatform.googleapis.com` (Agent Platform API)
* `logging.googleapis.com` (Cloud Logging API)
* `developerknowledge.googleapis.com` (Developer Knowledge API)

### 必要な IAM 権限
エージェントを実行するサービスアカウントには、以下の IAM ロールを付与する必要があります。

* **Agent Platform ユーザー** (`roles/aiplatform.user`)
* **Cloud Trace エージェント** (`roles/cloudtrace.agent`)
  * *※ランタイムによる Cloud Trace への実行トレース書き込みに必須です（付与しない場合、403エラーログが出力されます）。*
* **MCP ツールユーザー** (`roles/mcp.toolUser`)
* **Service Usage コンシューマー** (`roles/serviceusage.serviceUsageConsumer`)
  * *※リクエスト時に `X-Goog-User-Project` ヘッダーを送信し、プロジェクトのクォータを正しく消費するために必須です。*
* **モニタリング指標の書き込み** (`roles/monitoring.metricWriter`)
* **ログ閲覧者** (`roles/logging.viewer`)
* **ログ書き込み** (`roles/logging.logWriter`)

---

## 開発とデプロイ

### 1. ローカル開発環境のセットアップ

```bash
# 仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. Gemini Enterprise Agent Runtime へのデプロイ

以下の `adk deploy` コマンドを実行して、サービスアカウント構成（`sre_agent/SA_agent_engine_config.json`）を用いたエージェントのデプロイを行います。

```bash
adk deploy agent_engine --project=llm20260121 --region=us-central1 --display_name=SRE_Agent --agent_engine_config_file=$(pwd)/sre_agent/SA_agent_engine_config.json sre_agent
```
