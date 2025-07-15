#!/usr/bin/env python3
"""
IIIF Manifest Splitter
雅楽譜のIIIFマニフェストを楽曲ごとに分割するPythonスクリプト
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import copy

class IIIFManifestSplitter:
    def __init__(self, manifest_path: str, output_dir: str = None):
        """
        IIIFマニフェスト分割器を初期化
        
        Args:
            manifest_path: 元のマニフェストファイルのパス
            output_dir: 出力ディレクトリ（指定しない場合は元ファイルと同じディレクトリ）
        """
        self.manifest_path = Path(manifest_path)
        self.output_dir = Path(output_dir) if output_dir else self.manifest_path.parent
        self.manifest_data = None
        self.canvases = []
        
        # 出力ディレクトリを作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # マニフェストを読み込み
        self.load_manifest()
    
    def load_manifest(self):
        """マニフェストファイルを読み込む"""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                self.manifest_data = json.load(f)
            
            # キャンバスを抽出
            if 'sequences' in self.manifest_data and self.manifest_data['sequences']:
                self.canvases = self.manifest_data['sequences'][0].get('canvases', [])
            
            print(f"マニフェストを読み込みました: {len(self.canvases)}ページ")
            
        except Exception as e:
            raise Exception(f"マニフェストの読み込みに失敗しました: {e}")
    
    def split_manifest(self, title_pages: List[Dict[str, Any]], 
                      music_metadata: Dict[str, Any] = None,
                      gagaku_metadata_path: str = None) -> List[str]:
        """
        マニフェストを分割する
        
        Args:
            title_pages: タイトルページ情報のリスト
                        [{"page": 0, "titles": 1}, {"page": 3, "titles": 2}, ...]
            music_metadata: 楽曲メタデータ（従来形式、互換性のため）
            gagaku_metadata_path: 雅楽メタデータファイルのパス
        
        Returns:
            分割されたマニフェストファイルのパスのリスト
        """
        if not title_pages:
            raise ValueError("タイトルページが指定されていません")
        
        # 雅楽メタデータを読み込み
        gagaku_metadata = self.load_gagaku_metadata(gagaku_metadata_path)
        
        # タイトルページをページ番号でソート
        title_pages.sort(key=lambda x: x['page'])
        
        # 分割点を計算
        splits = self._calculate_splits(title_pages)
        
        # 分割マニフェストを生成
        output_files = []
        for i, split in enumerate(splits):
            manifest_file = self._create_split_manifest(split, i, music_metadata, gagaku_metadata)
            output_files.append(manifest_file)
        
        # 分割情報を保存
        self._save_split_info(title_pages, splits, output_files)
        
        return output_files
    
    def _calculate_splits(self, title_pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分割点を計算する（タイトルページから次のタイトルまでが1つの楽曲）"""
        if not title_pages:
            return []
        
        splits = []
        global_title_counter = 1  # グローバルなタイトル順序カウンター
        
        # 全てのタイトルを展開してソート
        all_titles = []
        for title_page in title_pages:
            page_number = title_page['page']  # 1ベースのページ番号
            page_index = page_number - 1      # 0ベースのインデックスに変換
            title_count = title_page['titles']
            for j in range(title_count):
                all_titles.append({
                    'page': page_index,  # 0ベースのインデックスを使用
                    'title_index': j + 1,
                    'total_titles': title_count,
                    'global_index': global_title_counter
                })
                global_title_counter += 1
        
        # ページ番号でソート
        all_titles.sort(key=lambda x: (x['page'], x['title_index']))
        
        # 各タイトルから次のタイトルまでを1つの楽曲として分割
        for i, title in enumerate(all_titles):
            start_page = title['page']
            
            # 同じページに複数のタイトルがある場合は、そのページのみ
            same_page_titles = [t for t in all_titles if t['page'] == start_page]
            if len(same_page_titles) > 1:
                end_page = start_page
            else:
                # 次のタイトルの開始ページを見つける
                if i + 1 < len(all_titles):
                    next_title = all_titles[i + 1]
                    end_page = next_title['page'] - 1
                else:
                    # 最後のタイトルの場合は最後のページまで
                    end_page = len(self.canvases) - 1
            
            # 楽曲の分割を追加
            splits.append({
                'start': start_page,
                'end': end_page,
                'type': 'track',  # タイトルを含む楽曲全体
                'title_count': 1,
                'title_index': title['title_index'],
                'total_titles': title['total_titles'],
                'global_title_index': title['global_index']
            })
        
        return splits
    
    def _create_split_manifest(self, split: Dict[str, Any], index: int, 
                             music_metadata: Dict[str, Any] = None,
                             gagaku_metadata: Dict[str, Any] = None) -> str:
        """分割されたマニフェストを作成する"""
        # 元のマニフェストをコピー
        split_manifest = copy.deepcopy(self.manifest_data)
        
        # IDとラベルを更新
        original_id = split_manifest.get('@id', '')
        base_name = self.manifest_path.stem
        new_filename = f"{base_name}_split{index + 1:03d}.json"
        new_id = original_id.replace(self.manifest_path.name, new_filename)
        split_manifest['@id'] = new_id
        
        # ラベルを更新
        original_label = split_manifest.get('label', '')
        if split.get('total_titles', 1) > 1:
            page_range = f"ページ{split['start'] + 1}" if split['start'] == split['end'] else f"ページ{split['start'] + 1}-{split['end'] + 1}"
            new_label = f"{original_label} - 楽曲{index + 1:03d} ({page_range} タイトル{split['title_index']}/{split['total_titles']})"
        else:
            page_range = f"ページ{split['start'] + 1}" if split['start'] == split['end'] else f"ページ{split['start'] + 1}-{split['end'] + 1}"
            new_label = f"{original_label} - 楽曲{index + 1:03d} ({page_range})"
        
        # 雅楽メタデータがある場合、より詳細なラベルを作成
        if gagaku_metadata and split['type'] == 'track':
            title_order = split.get('global_title_index', index + 1)
            track_meta = self.get_track_metadata(gagaku_metadata, title_order)
            if track_meta.get('track_title'):
                page_range = f"ページ{split['start'] + 1}" if split['start'] == split['end'] else f"ページ{split['start'] + 1}-{split['end'] + 1}"
                new_label = f"{track_meta['track_title']} ({track_meta.get('key', '')}) - {page_range}"
                # 一意なIDを設定
                split_manifest['@id'] = original_id.replace(self.manifest_path.name, 
                                                          f"{track_meta['track_id']}_manifest.json")
        
        split_manifest['label'] = new_label
        
        # キャンバスを抽出
        relevant_canvases = self.canvases[split['start']:split['end'] + 1]
        split_manifest['sequences'][0]['canvases'] = relevant_canvases
        
        # メタデータを更新
        self._update_metadata(split_manifest, split, index, music_metadata, gagaku_metadata)
        
        # ファイルに保存
        output_path = self.output_dir / new_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(split_manifest, f, ensure_ascii=False, indent=2)
        
        print(f"分割マニフェストを作成: {output_path}")
        return str(output_path)
    
    def _update_metadata(self, manifest: Dict[str, Any], split: Dict[str, Any], 
                        index: int, music_metadata: Dict[str, Any] = None,
                        gagaku_metadata: Dict[str, Any] = None):
        """マニフェストのメタデータを更新する"""
        if 'metadata' not in manifest:
            manifest['metadata'] = []
        
        # 分割情報を追加
        page_range = f"{split['start'] + 1}" if split['start'] == split['end'] else f"{split['start'] + 1}-{split['end'] + 1}"
        manifest['metadata'].append({
            'label': '楽曲範囲',
            'value': f"ページ {page_range}"
        })
        
        manifest['metadata'].append({
            'label': '分割タイプ',
            'value': '楽曲（タイトル含む）'
        })
        
        # 雅楽メタデータを追加
        if gagaku_metadata and split['type'] == 'track':
            title_order = split.get('global_title_index', index + 1)
            track_meta = self.get_track_metadata(gagaku_metadata, title_order)
            
            if track_meta:
                # 楽曲タイトル
                if track_meta.get('track_title'):
                    manifest['metadata'].append({
                        'label': '楽曲名',
                        'value': track_meta['track_title']
                    })
                
                # 一意なID
                if track_meta.get('track_id'):
                    manifest['metadata'].append({
                        'label': '楽曲ID',
                        'value': track_meta['track_id']
                    })
                
                # 調
                if track_meta.get('key'):
                    manifest['metadata'].append({
                        'label': '調',
                        'value': track_meta['key']
                    })
                
                # 部
                if track_meta.get('part'):
                    manifest['metadata'].append({
                        'label': '部',
                        'value': track_meta['part']
                    })
                
                # 撰定年
                if track_meta.get('compilation_year'):
                    manifest['metadata'].append({
                        'label': '撰定年',
                        'value': track_meta['compilation_year']
                    })
                
                # 譜集名
                if track_meta.get('book_title'):
                    manifest['metadata'].append({
                        'label': '譜集名',
                        'value': track_meta['book_title']
                    })
                
                # トラック番号
                if track_meta.get('track_index'):
                    manifest['metadata'].append({
                        'label': 'トラック番号',
                        'value': str(track_meta['track_index'])
                    })
        
        # 生成日時を追加
        manifest['metadata'].append({
            'label': '分割生成日時',
            'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # 従来の楽曲メタデータを追加（互換性のため）
        if music_metadata and str(index) in music_metadata:
            music_info = music_metadata[str(index)]
            
            if music_info.get('title'):
                manifest['metadata'].append({
                    'label': '楽曲名（従来）',
                    'value': music_info['title']
                })
            
            if music_info.get('category'):
                manifest['metadata'].append({
                    'label': '楽曲カテゴリ',
                    'value': music_info['category']
                })
            
            if music_info.get('description'):
                manifest['metadata'].append({
                    'label': '楽曲説明',
                    'value': music_info['description']
                })
            
            if music_info.get('composer'):
                manifest['metadata'].append({
                    'label': '作曲者',
                    'value': music_info['composer']
                })
            
            if music_info.get('period'):
                manifest['metadata'].append({
                    'label': '時代',
                    'value': music_info['period']
                })
    
    def _save_split_info(self, title_pages: List[Dict[str, Any]], 
                        splits: List[Dict[str, Any]], output_files: List[str]):
        """分割情報をJSONファイルに保存"""
        split_info = {
            'original_manifest': str(self.manifest_path),
            'split_date': datetime.now().isoformat(),
            'total_pages': len(self.canvases),
            'title_pages': title_pages,
            'splits': splits,
            'output_files': output_files
        }
        
        info_file = self.output_dir / f"{self.manifest_path.stem}_split_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(split_info, f, ensure_ascii=False, indent=2)
        
        print(f"分割情報を保存: {info_file}")
    
    def load_gagaku_metadata(self, metadata_path: str = None) -> Dict[str, Any]:
        """雅楽メタデータを読み込む"""
        if metadata_path is None:
            metadata_path = self.manifest_path.parent / "gagaku_titles_metadata.json"
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"雅楽メタデータの読み込みに失敗しました: {e}")
            return {}
    
    def extract_volume_info(self, manifest_path: str) -> Tuple[str, str]:
        """マニフェストパスから巻情報を抽出"""
        # volume数字_manifest.json から情報を抽出
        path_str = str(manifest_path)
        if 'volume' in path_str:
            import re
            match = re.search(r'volume(\d+)_manifest\.json', path_str)
            if match:
                volume_num = match.group(1)
                # g06_02 形式に変換
                return f"g06_{volume_num}", volume_num
        
        return None, None
    
    def get_track_metadata(self, gagaku_data: Dict[str, Any], title_order: int) -> Dict[str, Any]:
        """テーブル順序に基づいてトラックメタデータを取得"""
        if not gagaku_data or 'titles' not in gagaku_data:
            return {}
        
        # 全ての巻から全てのトラックを順序通りに収集
        all_tracks = []
        for volume_key in ['g06_02', 'g06_03', 'g06_04', 'g06_05', 'g06_6', 'g06_7']:
            volume_data = gagaku_data['titles'].get(volume_key, {})
            if volume_data and 'tracks' in volume_data:
                for track in volume_data['tracks']:
                    track_with_volume = track.copy()
                    track_with_volume.update({
                        'book_title': volume_data.get('book_title', ''),
                        'key': volume_data.get('key', ''),
                        'part': volume_data.get('part', ''),
                        'volume_key': volume_key
                    })
                    all_tracks.append(track_with_volume)
        
        # title_order は1ベースなので、0ベースに変換
        if 0 <= title_order - 1 < len(all_tracks):
            track = all_tracks[title_order - 1]
            return {
                'track_id': track.get('id', ''),
                'track_title': track.get('title', ''),
                'compilation_year': track.get('compilation_year', ''),
                'book_title': track.get('book_title', ''),
                'key': track.get('key', ''),
                'part': track.get('part', ''),
                'track_index': track.get('index', title_order),
                'volume_key': track.get('volume_key', '')
            }
        
        return {}

def load_title_pages_from_json(json_path: str) -> List[Dict[str, Any]]:
    """JSONファイルからタイトルページ情報を読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('title_pages', [])

def load_music_metadata_from_json(json_path: str) -> Dict[str, Any]:
    """JSONファイルから楽曲メタデータを読み込む"""
    if not os.path.exists(json_path):
        return {}
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description='IIIF Manifest Splitter')
    parser.add_argument('manifest', help='元のマニフェストファイルのパス')
    parser.add_argument('title_pages', help='タイトルページ情報のJSONファイルのパス')
    parser.add_argument('-o', '--output', help='出力ディレクトリ', default=None)
    parser.add_argument('-m', '--music-metadata', help='楽曲メタデータのJSONファイル（従来形式）', default=None)
    parser.add_argument('-g', '--gagaku-metadata', help='雅楽メタデータのJSONファイル', default='gagaku_titles_metadata.json')
    parser.add_argument('--dry-run', action='store_true', help='実際には分割せずに分割計画のみ表示')
    
    args = parser.parse_args()
    
    try:
        # タイトルページ情報を読み込み
        title_pages = load_title_pages_from_json(args.title_pages)
        if not title_pages:
            print("エラー: タイトルページ情報が見つかりません")
            return 1
        
        # 楽曲メタデータを読み込み（オプション）
        music_metadata = None
        if args.music_metadata:
            music_metadata = load_music_metadata_from_json(args.music_metadata)
        
        # 分割器を初期化
        splitter = IIIFManifestSplitter(args.manifest, args.output)
        
        if args.dry_run:
            # 分割計画のみ表示
            splits = splitter._calculate_splits(title_pages)
            
            print(f"\n=== 楽曲分割計画 ===")
            print(f"楽曲数: {len(splits)}個\n")
            
            for i, split in enumerate(splits):
                page_range = f"ページ{split['start'] + 1}" if split['start'] == split['end'] else f"ページ{split['start'] + 1}-{split['end'] + 1}"
                
                if split.get('total_titles', 1) > 1:
                    print(f"楽曲{i + 1:03d}: {page_range} (タイトル{split['title_index']}/{split['total_titles']}) - グローバル順序: {split['global_title_index']}")
                else:
                    print(f"楽曲{i + 1:03d}: {page_range} - グローバル順序: {split['global_title_index']}")
        else:
            # 実際に分割（雅楽メタデータを渡す）
            output_files = splitter.split_manifest(title_pages, music_metadata, args.gagaku_metadata)
            print(f"\n分割完了: {len(output_files)}個のマニフェストを生成しました")
        
        return 0
        
    except Exception as e:
        print(f"エラー: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
