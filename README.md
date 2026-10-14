# GCP SRE Agent (sre_agent)

このプロジェクトは、Gemini Enterprise Agent Runtime (旧 Vertex AI Agent Engine / Reasoning Engine) 上に構築およびデプロイ可能な、Google Cloud のインフラ監視・トラブルシューティング支援のための SRE AI エージェントです。

## 主な機能

* **GCP ログ調査**: [Google Cloud Logging MCP](https://logging.googleapis.com) と統合し、特定の GCP プロジェクトからエラーログや警告ログを高度にフィルタ・検索できます。
* **技術情報の提供**: [Google Developer Knowledge MCP](https://developerknowledge.googleapis.com) と統合し、Google Cloud や関連開発者製品の公式ドキュメント、ベストプラクティスに基づいた正確な技術情報を提供します。
* **高度な認証制御**: Application Default Credentials (ADC) を用いて認証トークンを動的に取得・キャッシュし、有効期限が切れた場合のみ自動でリフレッシュします。また、必要な `X-Goog-User-Project` ヘッダーを適切にインジェクトします。
* **リトライ制御とエラー回復**: `Gemini` モデルの `HttpRetryOptions` による LLM API リトライおよび ADK の `ReflectAndRetryToolPlugin` によるツール実行失敗時の自動再試行を備えています。
* **イベント履歴の自動圧縮 (Compaction)**: `EventsCompactionConfig` により、長期セッションや大量ログ調査時のコンテキストウィンドウ肥大化を自動で要約・圧縮します。

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
