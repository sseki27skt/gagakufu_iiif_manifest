#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本の伝統音楽楽譜のレイアウト認識スクリプト
縦書きテキストの行検出と文字領域認識を行います
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy import ndimage

def load_image(image_path):
    """画像を読み込む"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
    
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"画像を読み込めませんでした: {image_path}")
    
    return image

def detect_text_lines(image, expected_lines=3, include_title=False):
    """縦書きテキストの行を検出する（任意の行数に対応）"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # ノイズ除去とコントラスト強化
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 二値化（適応的閾値処理）
    binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    # 縦書き楽譜の水平プロジェクション（全体）
    height, width = binary.shape
    horizontal_projection = np.sum(binary, axis=0)
    
    # 全体の列検出（タイトル列も含む）
    from scipy.signal import find_peaks
    from scipy.ndimage import gaussian_filter1d
    
    # スムージング
    smoothed_projection = gaussian_filter1d(horizontal_projection, sigma=5)
    
    # 全ての有意なピークを検出
    threshold_height = np.max(smoothed_projection) * 0.2
    min_distance = width // (expected_lines + 2)  # タイトル列も考慮した最小距離
    
    peaks, properties = find_peaks(smoothed_projection, 
                                  distance=min_distance, 
                                  height=threshold_height,
                                  prominence=threshold_height * 0.3)
    
    # ピークから列境界を決定
    all_columns = []
    for peak in peaks:
        # ピーク周辺の境界を検出
        left_bound = peak
        right_bound = peak
        threshold = smoothed_projection[peak] * 0.1
        
        # 左側境界
        while left_bound > 0 and smoothed_projection[left_bound] > threshold:
            left_bound -= 1
        
        # 右側境界
        while right_bound < width - 1 and smoothed_projection[right_bound] > threshold:
            right_bound += 1
        
        # 最小幅チェック
        if right_bound - left_bound > 20:
            all_columns.append((left_bound, right_bound, peak))
    
    # 列を右から左の順序でソート（縦書きの読み順）
    all_columns.sort(key=lambda x: x[2], reverse=True)  # ピーク位置でソート
    
    # タイトル列の検出結果
    title_column = None
    
    # タイトル列と楽譜本文列を分離
    if include_title:
        # タイトル列も含めて解析
        if len(all_columns) >= expected_lines + 1:
            title_column = all_columns[0]  # 最も右の列がタイトル
            text_columns = all_columns[1:expected_lines+1]  # 2列目以降が楽譜本文
        else:
            # 検出列数が不足している場合
            text_columns = all_columns[:expected_lines]
            
        print(f"完全構造解析モード:")
        if title_column:
            print(f"  タイトル列: X座標 {title_column[0]}-{title_column[1]} (幅: {title_column[1]-title_column[0]}px)")
        print(f"  楽譜本文列数: {len(text_columns)}")
    else:
        # 楽譜本文のみを解析（従来の動作）
        if len(all_columns) >= expected_lines:
            # 最も右の列をタイトルとして除外（オプション）
            title_column = all_columns[0] if len(all_columns) > expected_lines else None
            
            # 楽譜本文の列を選択
            if len(all_columns) > expected_lines:
                # タイトル列を除いて、期待行数分を選択
                text_columns = all_columns[1:expected_lines+1]
            else:
                # 全ての列を楽譜本文として使用
                text_columns = all_columns[:expected_lines]
        else:
            # 検出された列が少ない場合は全てを使用
            text_columns = all_columns
    
    # タプルから座標のみを抽出
    text_columns = [(start, end) for start, end, _ in text_columns]
    
    # デバッグ情報（楽譜構造の理解のため）
    print(f"検出された総列数: {len(all_columns)}")
    if all_columns:
        rightmost_col = all_columns[0]  # 最も右の列（タイトル列の可能性）
        print(f"最右列（タイトル候補）: X座標 {rightmost_col[0]}-{rightmost_col[1]}")
    print(f"解析対象列数: {len(text_columns)}")
    
    # タイトル列情報も返す（将来の拡張用）
    title_info = {
        'detected': title_column is not None,
        'coordinates': title_column[:2] if title_column else None,
        'included_in_analysis': include_title
    }
    
    return binary, text_columns, horizontal_projection, title_info

def detect_character_regions(binary, text_columns):
    """各行内の文字領域を検出する（Shoga・Fuji部分のみ）"""
    character_regions = []
    
    for col_idx, (start_col, end_col) in enumerate(text_columns):
        # 各列内で縦方向のプロジェクション
        column_region = binary[:, start_col:end_col]
        vertical_projection = np.sum(column_region, axis=1)
        
        # 行内の水平プロジェクション（Shoga/Fuji/Hyoshi分析用）
        horizontal_projection = np.sum(column_region, axis=0)
        
        # Shogaピーク検出（最も高い密度の部分）
        from scipy.signal import find_peaks
        from scipy.ndimage import gaussian_filter1d
        
        smoothed_h_proj = gaussian_filter1d(horizontal_projection, sigma=2)
        peaks, _ = find_peaks(smoothed_h_proj, 
                             distance=10, 
                             height=np.max(smoothed_h_proj)*0.4)
        
        if len(peaks) > 0:
            # 最も高いピークをShogaとして特定
            shoga_peak = peaks[np.argmax(smoothed_h_proj[peaks])]
            shoga_center = start_col + shoga_peak
            
            # Shoga領域の境界決定
            col_width = end_col - start_col
            shoga_left = max(start_col, shoga_center - col_width//6)
            shoga_right = min(end_col, shoga_center + col_width//6)
            
            # Fuji領域（Shogaの左側）
            fuji_left = start_col
            fuji_right = shoga_left
            
            # Hyoshi領域（Shogaの右側）- 文字認識対象外
            hyoshi_left = shoga_right
            hyoshi_right = end_col
            
            print(f"行{col_idx+1}の構造:")
            print(f"  Fuji: X{fuji_left}-{fuji_right} (幅:{fuji_right-fuji_left}px)")
            print(f"  Shoga: X{shoga_left}-{shoga_right} (幅:{shoga_right-shoga_left}px)")
            print(f"  Hyoshi: X{hyoshi_left}-{hyoshi_right} (幅:{hyoshi_right-hyoshi_left}px)")
            
            # ShogaとFuji領域で文字検出
            for region_name, region_start, region_end in [
                ("Shoga", shoga_left, shoga_right),
                ("Fuji", fuji_left, fuji_right)
            ]:
                if region_end > region_start:
                    # 該当領域での縦方向プロジェクション
                    region_binary = binary[:, region_start:region_end]
                    region_v_proj = np.sum(region_binary, axis=1)
                    
                    # 文字の塊を検出
                    threshold = np.max(region_v_proj) * 0.15
                    char_rows = []
                    
                    in_char = False
                    start_row = 0
                    
                    for i, density in enumerate(region_v_proj):
                        if density > threshold and not in_char:
                            start_row = i
                            in_char = True
                        elif density <= threshold and in_char:
                            if i - start_row > 8:  # 最小高さフィルタ
                                char_rows.append((start_row, i, region_start, region_end, region_name))
                            in_char = False
                    
                    # 最後の文字が残っている場合
                    if in_char and len(region_v_proj) - start_row > 8:
                        char_rows.append((start_row, len(region_v_proj), region_start, region_end, region_name))
                    
                    character_regions.extend(char_rows)
        else:
            print(f"行{col_idx+1}: Shogaピークが検出されませんでした")
    
    return character_regions

def analyze_layout_structure(text_columns, character_regions, image_shape):
    """楽譜のレイアウト構造を分析する（Shoga/Fuji/Hyoshi構造対応）"""
    height, width = image_shape[:2]
    
    # 列（行）の統計
    num_lines = len(text_columns)
    line_widths = [end - start for start, end in text_columns]
    avg_line_width = np.mean(line_widths) if line_widths else 0
    
    # 文字領域の統計（ShogaとFujiのみ）
    num_characters = len(character_regions)
    
    # 各行の文字数とShoga/Fuji分析
    chars_per_line = []
    shoga_chars_per_line = []
    fuji_chars_per_line = []
    
    for start_col, end_col in text_columns:
        total_chars = 0
        shoga_chars = 0
        fuji_chars = 0
        
        for char_region in character_regions:
            if len(char_region) >= 5:  # 新しい形式（region_name含む）
                row_start, row_end, col_start, col_end, region_name = char_region
                if col_start >= start_col and col_end <= end_col:
                    total_chars += 1
                    if region_name == "Shoga":
                        shoga_chars += 1
                    elif region_name == "Fuji":
                        fuji_chars += 1
            else:  # 旧形式（互換性のため）
                row_start, row_end, col_start, col_end = char_region
                if col_start >= start_col and col_end <= end_col:
                    total_chars += 1
        
        chars_per_line.append(total_chars)
        shoga_chars_per_line.append(shoga_chars)
        fuji_chars_per_line.append(fuji_chars)
    
    # 行間隔の計算
    line_spacing = []
    if len(text_columns) > 1:
        for i in range(len(text_columns) - 1):
            spacing = text_columns[i+1][0] - text_columns[i][1]
            line_spacing.append(spacing)
    
    return {
        'num_lines': num_lines,
        'line_widths': line_widths,
        'avg_line_width': avg_line_width,
        'num_characters': num_characters,
        'chars_per_line': chars_per_line,
        'shoga_chars_per_line': shoga_chars_per_line,
        'fuji_chars_per_line': fuji_chars_per_line,
        'line_spacing': line_spacing,
        'avg_line_spacing': np.mean(line_spacing) if line_spacing else 0
    }

def visualize_layout_analysis(original_image, binary, text_columns, character_regions, horizontal_projection, title_info=None, output_file='score_layout_analysis.png', debug_mode=False, auto_estimate_info=None):
    """楽譜レイアウト解析結果を可視化する（Shoga/Fuji/Hyoshi構造対応）"""
    # 結果用の画像を作成
    result_image = original_image.copy()
    
    # タイトル列を描画（あれば）
    if title_info and title_info['detected'] and title_info['coordinates']:
        start_col, end_col = title_info['coordinates']
        # タイトル列は特別な色（金色）で描画
        cv2.rectangle(result_image, (start_col, 0), (end_col, original_image.shape[0]), (0, 215, 255), 3)
        cv2.putText(result_image, 'Title', (start_col, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 215, 255), 2)
    
    # テキスト行（列）と内部構造を描画
    for i, (start_col, end_col) in enumerate(text_columns):
        # 行全体の枠線
        color = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)][i % 6]
        cv2.rectangle(result_image, (start_col, 0), (end_col, original_image.shape[0]), color, 2)
        
        # 行番号を表示
        cv2.putText(result_image, f'Line {i+1}', (start_col, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # 行内構造の可視化（Shoga/Fuji/Hyoshi）
        col_width = end_col - start_col
        
        # 簡易的な内部構造推定（実際のピーク検出結果を使用すべき）
        binary_col = binary[:, start_col:end_col]
        h_proj = np.sum(binary_col, axis=0)
        
        if len(h_proj) > 0:
            from scipy.signal import find_peaks
            from scipy.ndimage import gaussian_filter1d
            smoothed = gaussian_filter1d(h_proj, sigma=2)
            peaks, _ = find_peaks(smoothed, distance=10, height=np.max(smoothed)*0.4)
            
            if len(peaks) > 0:
                shoga_peak = peaks[np.argmax(smoothed[peaks])]
                shoga_center = start_col + shoga_peak
                
                # 内部構造の境界
                shoga_left = max(start_col, shoga_center - col_width//6)
                shoga_right = min(end_col, shoga_center + col_width//6)
                fuji_right = shoga_left
                hyoshi_left = shoga_right
                
                # Fuji領域（薄い青）
                if fuji_right > start_col:
                    cv2.rectangle(result_image, (start_col, 10), (fuji_right, 40), (255, 200, 100), -1)
                    cv2.putText(result_image, 'F', (start_col + 5, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
                
                # Shoga領域（薄い赤）
                cv2.rectangle(result_image, (shoga_left, 10), (shoga_right, 40), (100, 100, 255), -1)
                cv2.putText(result_image, 'S', (shoga_left + 5, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
                
                # Hyoshi領域（薄い緑）
                if hyoshi_left < end_col:
                    cv2.rectangle(result_image, (hyoshi_left, 10), (end_col, 40), (100, 255, 100), -1)
                    cv2.putText(result_image, 'H', (hyoshi_left + 5, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    # 文字領域を描画（ShogaとFujiのみ、異なる色で）
    for char_region in character_regions:
        if len(char_region) >= 5:  # 新しい形式
            row_start, row_end, col_start, col_end, region_name = char_region
            if region_name == "Shoga":
                cv2.rectangle(result_image, (col_start, row_start), (col_end, row_end), (0, 0, 255), 2)  # 赤
            elif region_name == "Fuji":
                cv2.rectangle(result_image, (col_start, row_start), (col_end, row_end), (255, 0, 0), 2)  # 青
        else:  # 旧形式（互換性）
            row_start, row_end, col_start, col_end = char_region
            cv2.rectangle(result_image, (col_start, row_start), (col_end, row_end), (128, 255, 128), 1)
    
    # 結果を表示
    plt.figure(figsize=(20, 12))
    
    # 元画像
    plt.subplot(2, 3, 1)
    plt.imshow(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))
    plt.title('Original Score Image')
    plt.axis('off')
    
    # 二値化画像
    plt.subplot(2, 3, 2)
    plt.imshow(binary, cmap='gray')
    plt.title('Binarized Image')
    plt.axis('off')
    
    # 水平プロジェクション
    plt.subplot(2, 3, 3)
    plt.plot(horizontal_projection)
    plt.title('Horizontal Projection\n(Text Density)')
    plt.xlabel('Column (X-axis)')
    plt.ylabel('Character Density')
    plt.grid(True)
    
    # 自動推定情報の表示（常に表示）
    if auto_estimate_info:
        est_peaks = auto_estimate_info['peaks']
        smoothed_proj = auto_estimate_info['smoothed_projection']
        confidence = auto_estimate_info['confidence']
        
        # スムーズ化されたプロジェクションも表示
        plt.plot(smoothed_proj, 'r--', alpha=0.7, label='Smoothed')
        
        # 自動推定のピークをマーク
        plt.plot(est_peaks, smoothed_proj[est_peaks], "go", markersize=8, 
                label=f'Auto-Est Peaks ({len(est_peaks)} lines, conf: {confidence:.2f})')
        plt.legend()
    
    # デバッグモードでは追加情報を表示
    if debug_mode:
        # ピーク検出の詳細を表示
        from scipy.signal import find_peaks
        from scipy.ndimage import gaussian_filter1d
        smoothed = gaussian_filter1d(horizontal_projection, sigma=5)
        peaks, _ = find_peaks(smoothed, distance=30, height=np.max(smoothed)*0.3)
        plt.plot(peaks, smoothed[peaks], "rx", markersize=8, label='Detected Peaks')
        
        # 自動推定のピークも表示
        if auto_estimate_info:
            est_peaks = auto_estimate_info['peaks']
            plt.plot(est_peaks, smoothed[est_peaks], "go", markersize=10, label=f'Auto-Est Peaks (conf: {auto_estimate_info["confidence"]:.2f})')
        
        plt.legend()
    
    # 行検出結果
    line_detection_image = original_image.copy()
    
    # タイトル列も描画
    if title_info and title_info['detected'] and title_info['coordinates']:
        start_col, end_col = title_info['coordinates']
        cv2.rectangle(line_detection_image, (start_col, 0), (end_col, original_image.shape[0]), (0, 215, 255), 4)
    
    for i, (start_col, end_col) in enumerate(text_columns):
        color = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)][i % 6]
        cv2.rectangle(line_detection_image, (start_col, 0), (end_col, original_image.shape[0]), color, 3)
    
    plt.subplot(2, 3, 4)
    plt.imshow(cv2.cvtColor(line_detection_image, cv2.COLOR_BGR2RGB))
    title_text = 'Detected Text Lines\n(Shoga/Fuji/Hyoshi Structure)'
    if title_info and title_info['included_in_analysis']:
        title_text += '\n(Title included)'
    plt.title(title_text)
    plt.axis('off')
    
    # 文字領域検出結果（ShogaとFujiのみ）
    char_detection_image = original_image.copy()
    for char_region in character_regions:
        if len(char_region) >= 5:  # 新しい形式
            row_start, row_end, col_start, col_end, region_name = char_region
            if region_name == "Shoga":
                cv2.rectangle(char_detection_image, (col_start, row_start), (col_end, row_end), (0, 0, 255), 2)
            elif region_name == "Fuji":
                cv2.rectangle(char_detection_image, (col_start, row_start), (col_end, row_end), (255, 0, 0), 2)
        else:
            row_start, row_end, col_start, col_end = char_region
            cv2.rectangle(char_detection_image, (col_start, row_start), (col_end, row_end), (0, 255, 255), 1)
    
    plt.subplot(2, 3, 5)
    plt.imshow(cv2.cvtColor(char_detection_image, cv2.COLOR_BGR2RGB))
    plt.title('Character Regions\n(Shoga: Red, Fuji: Blue)')
    plt.axis('off')
    
    # 総合結果
    plt.subplot(2, 3, 6)
    plt.imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
    plt.title('Complete Layout Analysis\n(F:Fuji, S:Shoga, H:Hyoshi)')
    plt.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    if debug_mode:
        plt.show()
    else:
        plt.close()  # GUIなしの場合はクローズ

def print_layout_summary(layout_stats, expected_lines=3):
    """楽譜レイアウト解析結果のサマリーを出力（Shoga/Fuji/Hyoshi構造対応）"""
    print("=" * 60)
    print("日本伝統音楽楽譜 レイアウト解析結果")
    print("=" * 60)
    print(f"期待行数: {expected_lines}")
    print(f"検出された行数（縦書き列数）: {layout_stats['num_lines']}")
    print(f"総文字領域数: {layout_stats['num_characters']} (Shoga + Fujiのみ)")
    
    if layout_stats['line_widths']:
        print(f"行の平均幅: {layout_stats['avg_line_width']:.2f}ピクセル")
        print(f"最大行幅: {max(layout_stats['line_widths']):.2f}ピクセル")
        print(f"最小行幅: {min(layout_stats['line_widths']):.2f}ピクセル")
    
    if layout_stats['chars_per_line']:
        print(f"1行あたりの平均文字数: {np.mean(layout_stats['chars_per_line']):.1f}")
        print(f"最大文字数/行: {max(layout_stats['chars_per_line'])}")
        print(f"最小文字数/行: {min(layout_stats['chars_per_line'])}")
    
    # Shoga/Fuji分析結果
    if 'shoga_chars_per_line' in layout_stats and 'fuji_chars_per_line' in layout_stats:
        total_shoga = sum(layout_stats['shoga_chars_per_line'])
        total_fuji = sum(layout_stats['fuji_chars_per_line'])
        
        if total_shoga > 0 or total_fuji > 0:
            print(f"\n楽譜構造分析:")
            print(f"  総Shoga文字数: {total_shoga}")
            print(f"  総Fuji文字数: {total_fuji}")
            print(f"  Shoga/Fuji比率: {total_shoga/(total_shoga+total_fuji)*100:.1f}% / {total_fuji/(total_shoga+total_fuji)*100:.1f}%")
    
    if layout_stats['line_spacing']:
        print(f"行間の平均間隔: {layout_stats['avg_line_spacing']:.2f}ピクセル")
    
    print("\n各行の詳細:")
    for i, (width, char_count) in enumerate(zip(layout_stats['line_widths'], layout_stats['chars_per_line'])):
        shoga_count = layout_stats.get('shoga_chars_per_line', [0]*len(layout_stats['line_widths']))[i]
        fuji_count = layout_stats.get('fuji_chars_per_line', [0]*len(layout_stats['line_widths']))[i]
        
        line_detail = f"  行 {i+1}: 幅={width}px, 総文字数={char_count}"
        if shoga_count > 0 or fuji_count > 0:
            line_detail += f" (Shoga:{shoga_count}, Fuji:{fuji_count})"
        print(line_detail)
    
    print("\n楽譜の特徴:")
    # 楽譜の特徴を推定
    if layout_stats['num_lines'] >= 3:
        print("  - 複数行構成の楽譜です")
    else:
        print("  - 単純な構成の楽譜です")
    
    if layout_stats['chars_per_line'] and max(layout_stats['chars_per_line']) > 20:
        print("  - 長い楽句を含む楽譜です")
    
    if layout_stats['line_spacing'] and layout_stats['avg_line_spacing'] > 50:
        print("  - 行間が広く、読みやすいレイアウトです")
    elif layout_stats['line_spacing'] and layout_stats['avg_line_spacing'] < 30:
        print("  - 密なレイアウトの楽譜です")
    
    # Shoga/Fuji構造の特徴
    if 'shoga_chars_per_line' in layout_stats and 'fuji_chars_per_line' in layout_stats:
        total_shoga = sum(layout_stats['shoga_chars_per_line'])
        total_fuji = sum(layout_stats['fuji_chars_per_line'])
        
        if total_shoga > total_fuji:
            print("  - Shoga主体の楽譜です（歌詞・音符重視）")
        elif total_fuji > total_shoga:
            print("  - Fuji主体の楽譜です（装飾・補助記号重視）")
        else:
            print("  - Shoga・Fujiバランス型の楽譜です")
    
    # 認識精度の評価
    accuracy = "高" if layout_stats['num_lines'] == expected_lines else "要調整"
    print(f"  - 認識精度: {accuracy}")
    
    if layout_stats['num_lines'] != expected_lines:
        print(f"    推奨: パラメータ調整または期待行数の再検討をお勧めします")
    
    print("\n構造説明:")
    print("  - Shoga: 歌詞・音符（ピーク部分、文字認識対象）")
    print("  - Fuji: 装飾・補助記号（Shogaの左側、文字認識対象）")
    print("  - Hyoshi: 拍子・リズム記号（Shogaの右側、文字認識対象外）")

def estimate_line_count_from_projection(horizontal_projection, image_width):
    """水平プロジェクションのピーク数から楽譜本文の行数を自動推定する"""
    from scipy.signal import find_peaks
    from scipy.ndimage import gaussian_filter1d
    
    # スムージング
    smoothed_projection = gaussian_filter1d(horizontal_projection, sigma=5)
    
    # 複数の閾値で試行し、最適な行数を決定
    max_projection = np.max(smoothed_projection)
    
    # 異なる閾値での検出結果を評価
    threshold_ratios = [0.15, 0.2, 0.25, 0.3]
    distance_ratios = [0.08, 0.1, 0.12]  # 画像幅に対する比率
    
    candidates = []
    
    for threshold_ratio in threshold_ratios:
        for distance_ratio in distance_ratios:
            threshold_height = max_projection * threshold_ratio
            min_distance = int(image_width * distance_ratio)
            
            peaks, properties = find_peaks(smoothed_projection,
                                         distance=min_distance,
                                         height=threshold_height,
                                         prominence=threshold_height * 0.3)
            
            # ピークの品質評価
            if len(peaks) > 0:
                # ピーク高さの一貫性
                peak_heights = smoothed_projection[peaks]
                height_std = np.std(peak_heights) / np.mean(peak_heights) if len(peak_heights) > 1 else 0
                
                # ピーク間隔の一貫性
                if len(peaks) > 1:
                    intervals = np.diff(np.sort(peaks))
                    interval_std = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else float('inf')
                else:
                    interval_std = 0
                
                # 信頼度スコア（低いほど良い）
                confidence = height_std + interval_std * 0.5
                
                candidates.append({
                    'count': len(peaks),
                    'confidence': confidence,
                    'peaks': peaks,
                    'threshold': threshold_height,
                    'distance': min_distance,
                    'peak_heights': peak_heights
                })
    
    if not candidates:
        # フォールバック: 非常に緩い条件で再試行
        threshold_height = max_projection * 0.1
        min_distance = image_width // 10
        peaks, _ = find_peaks(smoothed_projection,
                            distance=min_distance,
                            height=threshold_height)
        estimated_lines = max(1, len(peaks))
        confidence = 0.5  # 低い信頼度
        print(f"⚠️ フォールバック推定: {estimated_lines}行 (信頼度: 低)")
        return estimated_lines, confidence, peaks, smoothed_projection
    
    # 最も信頼度の高い（confidenceが最小の）候補を選択
    best_candidate = min(candidates, key=lambda x: x['confidence'])
    estimated_lines = best_candidate['count']
    
    # 信頼度の調整（3-6行の範囲内なら信頼度を上げる）
    if 3 <= estimated_lines <= 6:
        confidence = max(0.7, 1.0 - best_candidate['confidence'])
    else:
        confidence = max(0.3, 0.7 - best_candidate['confidence'])
    
    print(f"🔍 行数自動推定:")
    print(f"   推定行数: {estimated_lines}行")
    print(f"   信頼度: {confidence:.2f}")
    print(f"   検出ピーク数: {len(best_candidate['peaks'])}")
    print(f"   使用閾値: {best_candidate['threshold']:.1f}")
    
    if confidence < 0.5:
        print(f"⚠️ 注意: 推定の信頼度が低いです。手動で行数を指定することをお勧めします。")
    
    return estimated_lines, confidence, best_candidate['peaks'], smoothed_projection

def main():
    """メイン関数"""
    import sys
    import argparse
    
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='日本の伝統音楽楽譜のレイアウト認識')
    parser.add_argument('--image', '-i', default='図1.png', 
                        help='楽譜画像のパス (デフォルト: 図1.png)')
    parser.add_argument('--lines', '-l', type=int, default=None,
                        help='期待する行数 (デフォルト: 自動推定)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='デバッグモードで実行')
    parser.add_argument('--output', '-o', default='score_layout_analysis.png',
                        help='出力画像のファイル名 (デフォルト: score_layout_analysis.png)')
    parser.add_argument('--include-title', '-t', action='store_true',
                        help='タイトル列も含めて解析（縦書き楽譜の完全構造）')
    parser.add_argument('--manual-lines', '-m', action='store_true',
                        help='自動推定を無効化し、手動指定を強制')
    
    # 引数が少ない場合の簡単な指定方法をサポート
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        # "python object_detection.py 5" のような簡単な指定をサポート
        expected_lines = int(sys.argv[1])
        image_path = "図1.png"
        debug_mode = False
        output_file = 'score_layout_analysis.png'
        include_title = False
        auto_estimate = False
        print(f"簡単モード: 行数={expected_lines}, 画像=図1.png")
    else:
        args = parser.parse_args()
        expected_lines = args.lines
        image_path = args.image
        debug_mode = args.debug
        output_file = args.output
        include_title = args.include_title
        manual_lines = args.manual_lines
    
    if debug_mode:
        print("=== デバッグモードで実行中 ===")
    
    # 行数の決定（デフォルトで自動推定、--manual-linesで無効化）
    use_auto_estimate = not manual_lines and expected_lines is None
    
    print(f"設定:")
    print(f"  画像ファイル: {image_path}")
    if use_auto_estimate:
        print(f"  行数: 自動推定")
    else:
        print(f"  期待行数: {expected_lines}")
    print(f"  出力ファイル: {output_file}")
    print(f"  デバッグモード: {'ON' if debug_mode else 'OFF'}")
    print(f"  タイトル列含む: {'ON' if include_title else 'OFF'}")
    print(f"  楽譜構造: 縦書き（右→左、上→下）")
    
    try:
        # 画像を読み込み
        print(f"楽譜画像を読み込み中: {image_path}")
        image = load_image(image_path)
        print(f"画像サイズ: {image.shape}")
        
        # 行数の自動推定（必要な場合）
        if use_auto_estimate:
            print("水平プロジェクションから行数を自動推定中...")
            
            # 初期プロジェクション取得（推定用）
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)
            binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY_INV, 11, 2)
            initial_projection = np.sum(binary, axis=0)
            
            estimated_lines, confidence, detected_peaks, smoothed_proj = estimate_line_count_from_projection(
                initial_projection, image.shape[1])
            
            # 推定結果を使用
            expected_lines = estimated_lines
            print(f"✅ 自動推定結果: {expected_lines}行")
            print(f"   信頼度: {confidence:.3f}")
            
            if confidence < 0.5:
                print(f"⚠️ 推定の信頼度が低いため、注意深く結果を確認してください。")
        
        # 縦書きテキスト行検出
        print(f"縦書きテキスト行を検出中（目標行数: {expected_lines}行）...")
        binary, text_columns, horizontal_projection, title_info = detect_text_lines(image, expected_lines, include_title)
        
        # 文字領域検出
        print("文字領域を検出中...")
        character_regions = detect_character_regions(binary, text_columns)
        
        # レイアウト構造分析
        print("レイアウト構造を分析中...")
        layout_stats = analyze_layout_structure(text_columns, character_regions, image.shape)
        
        # 結果の可視化
        print("結果を可視化中...")
        
        # 自動推定の情報も可視化に渡す
        auto_estimate_info = None
        if use_auto_estimate:
            auto_estimate_info = {
                'peaks': detected_peaks,
                'smoothed_projection': smoothed_proj,
                'confidence': confidence
            }
        
        visualize_layout_analysis(image, binary, text_columns, character_regions, 
                                 horizontal_projection, title_info, output_file, debug_mode, auto_estimate_info)
        
        # サマリー出力
        print_layout_summary(layout_stats, expected_lines)
        
        print("楽譜レイアウト解析が完了しました！")
        print(f"結果画像が '{output_file}' として保存されました。")
        
        # 検出結果の評価
        detected_lines = layout_stats['num_lines']
        if use_auto_estimate:
            print(f"📊 自動推定評価:")
            print(f"   推定行数: {expected_lines}")
            print(f"   検出行数: {detected_lines}")
            if detected_lines == expected_lines:
                print(f"✅ EXCELLENT: 自動推定が正確でした！")
            elif abs(detected_lines - expected_lines) == 1:
                print(f"✅ GOOD: 自動推定がほぼ正確でした（差:±1行）")
            else:
                print(f"⚠️ NOTICE: 自動推定に誤差があります（差:{abs(detected_lines - expected_lines)}行）")
                print(f"   手動で行数を指定することをお勧めします: --lines {detected_lines}")
        else:
            if detected_lines == expected_lines:
                print(f"✅ SUCCESS: 期待通り{expected_lines}行構成が検出されました！")
            else:
                print(f"⚠️ NOTICE: {detected_lines}行が検出されました（期待値: {expected_lines}行）")
                print("   パラメータ調整により精度向上が可能です。")
            
        if debug_mode:
            print("\n=== デバッグ情報 ===")
            print(f"検出された列の座標:")
            for i, (start, end) in enumerate(text_columns):
                print(f"  行{i+1}: X座標 {start}-{end} (幅: {end-start}px)")
            
            if title_info['detected']:
                if title_info['coordinates']:
                    start, end = title_info['coordinates']
                    print(f"  タイトル列: X座標 {start}-{end} (幅: {end-start}px)")
                print(f"  タイトル列解析: {'含む' if title_info['included_in_analysis'] else '除外'}")
            
            print(f"水平プロジェクション統計:")
            print(f"  最大値: {np.max(horizontal_projection)}")
            print(f"  平均値: {np.mean(horizontal_projection):.2f}")
            print(f"  標準偏差: {np.std(horizontal_projection):.2f}")
        
    except FileNotFoundError as e:
        print(f"エラー: {e}")
        print("図1.pngファイルが同じディレクトリに存在することを確認してください。")
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
