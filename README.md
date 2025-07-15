# 雅楽譜 IIIF マニフェスト分割ツール

このツールは、雅楽譜のIIIFマニフェストを楽曲ごとに分割するためのWebアプリケーションとPythonスクリプトの組み合わせです。

## 機能

- **Webブラウザでの画像確認**: IIIFマニフェストの画像を一覧表示
- **タイトルページのマーキング**: ブラウザ上でタイトルページをマーク
- **ローカルファイル対応**: 任意のローカルIIIFマニフェストを読み込み可能
- **Pythonでの分割処理**: 高精度なマニフェスト分割とメタデータ付与
- **タイトルページ情報のエクスポート**: マーキング結果をJSONファイルで出力

## システム構成

1. **Webアプリケーション** (JavaScript): 画像表示・タイトルページマーキング
2. **分割スクリプト** (Python): マニフェスト分割・メタデータ付与

## 使用方法

### 1. サーバーの起動

```bash
python3 server.py 8080
```

### 2. Webアプリケーションでタイトルページをマーク

ブラウザで `http://localhost:8080/manuscript_splitter.html` にアクセス

1. **マニフェストソース選択**:
   - 既存コレクション: 100270332または100376839から選択
   - ローカルファイル: 任意のIIIFマニフェストJSONファイルを選択

2. **マニフェスト読み込み**: 「マニフェスト読み込み」ボタンをクリック

3. **タイトルページのマーキング**:
   - 画像をクリックしてタイトルページをマーク
   - 「タイトル数」フィールドで1ページ内のタイトル数を指定
   - 複数のタイトルがある場合は対応する数値を入力

4. **タイトルページ情報のエクスポート**: 「タイトルページ情報をエクスポート」ボタンでJSONファイルを保存

5. **Pythonコマンドの取得**: 「Python分割コマンド表示」ボタンで実行コマンドを表示

### 3. Pythonスクリプトでマニフェスト分割

```bash
python3 iiif_manifest_splitter.py "manifest.json" "title_pages.json" -m "music_metadata.json"
```

#### コマンドオプション

- `manifest.json`: 元のマニフェストファイル
- `title_pages.json`: Webアプリでエクスポートしたタイトルページ情報
- `-m, --music-metadata`: 楽曲メタデータファイル（オプション）
- `-o, --output`: 出力ディレクトリ（デフォルト: 元ファイルと同じディレクトリ）
- `--dry-run`: 実際には分割せず、分割計画のみ表示

#### 使用例

```bash
# 基本的な分割
python3 iiif_manifest_splitter.py "100376839/volume0_manifest.json" "volume0_title_pages.json"

# 楽曲メタデータ付きで分割
python3 iiif_manifest_splitter.py "100376839/volume0_manifest.json" "volume0_title_pages.json" -m "music_metadata.json"

# 出力ディレクトリを指定
python3 iiif_manifest_splitter.py "manifest.json" "title_pages.json" -o "./split_output"

# 分割計画の確認のみ
python3 iiif_manifest_splitter.py "manifest.json" "title_pages.json" --dry-run
```

## ファイル構成

```
manuscript_splitter.html     # メインのWebアプリケーション
manuscript_splitter.js       # JavaScript ロジック
music_metadata_editor.js     # 楽曲メタデータ編集機能
iiif_manifest_splitter.py    # Python分割スクリプト
server.py                    # CORS対応HTTPサーバー
music_metadata.json          # 楽曲メタデータ設定
sample_title_pages.json      # サンプルタイトルページ情報
README.md                    # このファイル
```

## ファイル形式

### タイトルページ情報 (JSON)

```json
{
  "manifest_file": "100376839/volume0_manifest.json",
  "export_date": "2025-01-12T10:30:00.000Z",
  "title_pages": [
    {
      "page": 0,
      "titles": 1
    },
    {
      "page": 3,
      "titles": 2
    },
    {
      "page": 7,
      "titles": 1
    }
  ]
}
```

### 楽曲メタデータ (JSON)

```json
{
  "0": {
    "title": "楽曲名",
    "category": "神楽",
    "description": "楽曲の説明",
    "composer": "作曲者名",
    "period": "明治時代"
  }
}
```

## 分割ロジック

1. **ページ分析**: タイトルページを基準に分割点を決定
2. **セクション分割**: 
   - 前のコンテンツ → 1つのマニフェスト
   - タイトルページ → タイトル数分のマニフェスト
   - 次のタイトルページまでのコンテンツ → 1つのマニフェスト
3. **メタデータ付与**: 各分割マニフェストに情報を自動追加

## 出力ファイル

### 分割マニフェスト

- `[元ファイル名]_split001.json`, `[元ファイル名]_split002.json`, ...
- 各ファイルには元のメタデータ + 分割情報 + 楽曲情報が含まれる

### 分割情報

- `[元ファイル名]_split_info.json`: 分割処理の詳細情報

## 技術仕様

- **フロントエンド**: HTML5, CSS3, JavaScript (ES6+)
- **バックエンド**: Python 3.7+
- **IIIF**: IIIF Presentation API 2.0準拠
- **ブラウザサポート**: モダンブラウザ（Chrome, Firefox, Safari, Edge）

## 注意事項

- Webアプリケーションは画像表示とマーキングのみを行います
- 実際のマニフェスト分割はPythonスクリプトで実行してください
- 大きな画像の読み込みには時間がかかる場合があります
- ローカルファイルを使用する場合は、適切なパスでPythonスクリプトを実行してください
