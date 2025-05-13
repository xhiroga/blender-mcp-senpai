# ADR

## Tool

### ジオメトリノード

NodeTreeは`.blend`に格納した。テスト用のメッシュまで単一RepoでGit管理できるのでありがたい。  
Python内部にデータを持つのはメンテナンス性が低いので見送り。また、アセットのオンライン化についてはAPIの実装を待つ方針とする。

## チャットUI

### 技術選定

このリポジトリの価値は、Blenderの言語化にある。チャットUIはPlug and Playの電池の役割。  
ライブラリとしてはGradioを選定した。これはPythonのみでUIをホストする際に相性が良いと考えたため。  
Pythonにおけるその他の選択肢としては、Streamlit や Chinlit がある。更新頻度と検索のしやすさを考えてGradioを選定した。  

JS/TSのUIライブラリを用いてフロントエンドをビルドし、それを Starlette でホストする選択肢もある。  
これはBlender側とチャット側の通信経路をMCPに限定する意味でも積極的に検討したい。  

ライブラリとして利用できそうなのは、AI SDK, LangChain Agent Chat UI, assistant-ui など。  
特にAI SDK + assistant-ui が良さそうだが、Static export した状態で AI SDKを利用できないのでしばらく静観。

参考: <https://github.com/vercel/ai/issues/5140>

### データの流れ

まずは [Managing State](https://www.gradio.app/guides/state-in-blocks) を参照。  
コンポーネント側に状態を閉じ込め、イベントリスナーは純粋関数で書きたかったが、ページのロード時のStateの初期化で最新のDBの値を取得することが難しかった。  
代替案として、永続化されているデータのみイベントリスナーから直接参照している。

### 永続化

APIキーの永続化には`keyring`を用いた。独自に暗号化を実装するコストが高いと判断したため。

`keyring`で保存したAPIキーをUIから閲覧する手順は次のとおり。

- Windows: コントロール パネル → 資格情報マネージャー → "Windows 資格情報" → 汎用資格情報の一覧から `blender_senpai` を探し、該当エントリ（ユーザー名 = プロバイダー名）を開く。
- macOS: Spotlight 等で「キーチェーンアクセス」を開き、左ペインで「ログイン」を選択。検索フィールドに `blender_senpai` と入力し、サービスが `blender_senpai` の項目をダブルクリックするとパスワード表示（要 Touch ID / パスワード）。
- Linux: TODO...
