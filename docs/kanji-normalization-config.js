/**
 * 旧字正規化設定ファイル
 * 
 * 新しい旧字-新字ペアを追加する場合は、KANJI_NORMALIZATION_CONFIG オブジェクトに
 * 追加してください。
 * 
 * 使用例:
 * - コンソールで addKanjiNormalization('團', '団') を実行
 * - または、このファイルを直接編集
 */

// 旧字正規化マッピング設定
const KANJI_NORMALIZATION_CONFIG = {
    // ========================================
    // 現在使用中の旧字ペア
    // ========================================
    
    // 音楽関連
    '樂': '楽',        // 還城樂 → 還城楽 (6箇所で使用)
    
    // 楽器関連  
    '龍': '竜',        // 龍笛 → 竜笛 (111箇所で使用)
    
    // ========================================
    // 将来の拡張用（必要に応じてコメントアウトを外す）
    // ========================================
    
    // 一般的な旧字
    // '團': '団',     // 壱団嬌 → 壱団嬌
    // '學': '学',     // 學校 → 学校
    // '藝': '芸',     // 藝術 → 芸術
    // '國': '国',     // 國楽 → 国楽
    // '變': '変',     // 變奏 → 変奏
    // '聲': '声',     // 聲楽 → 声楽
    // '實': '実',     // 實際 → 実際
    // '會': '会',     // 會議 → 会議
    // '當': '当',     // 當時 → 当時
    // '體': '体',     // 體系 → 体系
    
    // 数字関連
    '壹': '壱',     // 壹越調 → 壱越調
    // '貳': '弐',     // 貳越調 → 弐越調
    // '參': '参',     // 參越調 → 参越調
    // '肆': '四',     // 肆越調 → 四越調
    
    // 音楽用語
    '絃': '弦',     // 絃楽器 → 弦楽器
    // '調': '調',     // 調子 → 調子 (同じなので不要)
    // '管': '管',     // 管楽器 → 管楽器 (同じなので不要)
};

/**
 * 旧字正規化マッピングを取得する関数
 * @returns {Object} 旧字正規化マッピング
 */
function getKanjiNormalizationConfig() {
    return KANJI_NORMALIZATION_CONFIG;
}

/**
 * 設定に新しい旧字-新字ペアを追加する関数
 * @param {string} oldKanji - 旧字
 * @param {string} newKanji - 新字
 */
function addToConfig(oldKanji, newKanji) {
    KANJI_NORMALIZATION_CONFIG[oldKanji] = newKanji;
    console.log(`設定に追加: ${oldKanji} → ${newKanji}`);
    console.log('変更を永続化するには、このファイルを保存してください。');
}

/**
 * 現在の設定を表示する関数
 */
function showConfig() {
    console.log('='.repeat(50));
    console.log('旧字正規化設定:');
    console.log('='.repeat(50));
    
    let activeCount = 0;
    for (const [oldKanji, newKanji] of Object.entries(KANJI_NORMALIZATION_CONFIG)) {
        console.log(`  ${oldKanji} → ${newKanji}`);
        activeCount++;
    }
    
    console.log('='.repeat(50));
    console.log(`合計: ${activeCount} ペア`);
    console.log('='.repeat(50));
}

// ブラウザで利用可能にする
if (typeof window !== 'undefined') {
    window.KANJI_NORMALIZATION_CONFIG = KANJI_NORMALIZATION_CONFIG;
    window.getKanjiNormalizationConfig = getKanjiNormalizationConfig;
    window.addToConfig = addToConfig;
    window.showConfig = showConfig;
}

// Node.js環境での利用（将来の拡張用）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        KANJI_NORMALIZATION_CONFIG,
        getKanjiNormalizationConfig,
        addToConfig,
        showConfig
    };
}
