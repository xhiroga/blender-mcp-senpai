# ADR

## Tool

### ジオメトリノード

NodeTreeは`.blend`に格納した。テスト用のメッシュまで単一RepoでGit管理できるのでありがたい。  
Python内部にデータを持つのはメンテナンス性が低いので見送り。また、アセットのオンライン化についてはAPIの実装を待つ方針とする。

## チャットUI

### 技術選定

このリポジトリの価値は、Blenderの言語化にある。チャットUIはPlug and Playの電池の役割。  
フロントエンドには、利用者数が多くエコシステムが整っているAI SDK + assistant-ui を選定した。ただし、Blender拡張に同梱するためにStatic export が必須となる。

そのため、チャットAPIとの通信には工夫が必要となる。参考: <https://github.com/vercel/ai/issues/5140>

### 永続化

APIキーの永続化には`keyring`を用いた。独自に暗号化を実装するコストが高いと判断したため。

`keyring`で保存したAPIキーをUIから閲覧する手順は次のとおり。

- Windows: コントロール パネル → 資格情報マネージャー → "Windows 資格情報" → 汎用資格情報の一覧から `blender_senpai` を探し、該当エントリ（ユーザー名 = プロバイダー名）を開く。
- macOS: Spotlight 等で「キーチェーンアクセス」を開き、左ペインで「ログイン」を選択。検索フィールドに `blender_senpai` と入力し、サービスが `blender_senpai` の項目をダブルクリックするとパスワード表示（要 Touch ID / パスワード）。
- Linux: TODO...
