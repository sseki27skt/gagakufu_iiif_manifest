/**
 * 楽曲メタデータエディター
 * 分割されたマニフェストに楽曲情報を手動で割り当てるためのダイアログ
 */
class MusicMetadataEditor {
    constructor(parentApp) {
        this.parentApp = parentApp;
        this.currentSplits = [];
        this.musicAssignments = new Map(); // splitIndex -> musicInfo
    }

    show(splits) {
        this.currentSplits = splits;
        this.createDialog();
    }

    createDialog() {
        // 既存のダイアログがあれば削除
        const existingDialog = document.getElementById('musicMetadataDialog');
        if (existingDialog) {
            existingDialog.remove();
        }

        const dialog = document.createElement('div');
        dialog.id = 'musicMetadataDialog';
        dialog.className = 'metadata-dialog';
        dialog.innerHTML = this.getDialogHTML();

        document.body.appendChild(dialog);
        this.initializeDialogEvents();
    }

    getDialogHTML() {
        return `
            <div class="metadata-dialog-overlay">
                <div class="metadata-dialog-content">
                    <div class="metadata-dialog-header">
                        <h3>楽曲メタデータの編集</h3>
                        <button class="close-dialog" type="button">×</button>
                    </div>
                    <div class="metadata-dialog-body">
                        <p>各分割マニフェストに楽曲情報を割り当ててください：</p>
                        <div id="musicAssignmentList" class="music-assignment-list">
                            ${this.generateAssignmentItems()}
                        </div>
                    </div>
                    <div class="metadata-dialog-footer">
                        <button id="cancelMetadata" class="btn-secondary">キャンセル</button>
                        <button id="applyMetadata" class="btn-primary">適用</button>
                    </div>
                </div>
            </div>
        `;
    }

    generateAssignmentItems() {
        return this.currentSplits.map((split, index) => {
            const info = split.info;
            const pageRange = info.start === info.end ? `ページ ${info.start}` : `ページ ${info.start}-${info.end}`;
            const typeText = info.type === 'title' ? 'タイトルページ' : 'コンテンツページ';
            
            return `
                <div class="assignment-item" data-split-index="${index}">
                    <div class="assignment-header">
                        <strong>分割${index + 1}</strong> - ${pageRange} - ${typeText}
                    </div>
                    <div class="assignment-fields">
                        <div class="field-group">
                            <label>楽曲名:</label>
                            <input type="text" name="title" placeholder="楽曲名を入力" />
                        </div>
                        <div class="field-group">
                            <label>カテゴリ:</label>
                            <select name="category">
                                <option value="">選択してください</option>
                                <option value="神楽">神楽</option>
                                <option value="舞楽">舞楽</option>
                                <option value="管弦">管弦</option>
                                <option value="歌曲">歌曲</option>
                                <option value="催馬楽">催馬楽</option>
                                <option value="朗詠">朗詠</option>
                                <option value="東遊">東遊</option>
                                <option value="その他">その他</option>
                            </select>
                        </div>
                        <div class="field-group">
                            <label>説明:</label>
                            <textarea name="description" placeholder="楽曲の説明を入力" rows="2"></textarea>
                        </div>
                        <div class="field-group">
                            <label>作曲者:</label>
                            <input type="text" name="composer" placeholder="作曲者名" />
                        </div>
                        <div class="field-group">
                            <label>時代:</label>
                            <input type="text" name="period" placeholder="時代・年代" />
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    initializeDialogEvents() {
        // 閉じるボタン
        document.querySelector('.close-dialog').addEventListener('click', () => {
            this.close();
        });

        // キャンセルボタン
        document.getElementById('cancelMetadata').addEventListener('click', () => {
            this.close();
        });

        // 適用ボタン
        document.getElementById('applyMetadata').addEventListener('click', () => {
            this.applyMetadata();
        });

        // オーバーレイクリックで閉じる
        document.querySelector('.metadata-dialog-overlay').addEventListener('click', (e) => {
            if (e.target.classList.contains('metadata-dialog-overlay')) {
                this.close();
            }
        });

        // 入力フィールドの自動保存
        document.querySelectorAll('.assignment-item input, .assignment-item select, .assignment-item textarea').forEach(input => {
            input.addEventListener('change', () => {
                this.saveAssignment();
            });
        });
    }

    saveAssignment() {
        document.querySelectorAll('.assignment-item').forEach((item, index) => {
            const title = item.querySelector('[name="title"]').value;
            const category = item.querySelector('[name="category"]').value;
            const description = item.querySelector('[name="description"]').value;
            const composer = item.querySelector('[name="composer"]').value;
            const period = item.querySelector('[name="period"]').value;

            if (title || category || description || composer || period) {
                this.musicAssignments.set(index, {
                    title,
                    category,
                    description,
                    composer,
                    period
                });
            } else {
                this.musicAssignments.delete(index);
            }
        });
    }

    applyMetadata() {
        this.saveAssignment();
        
        // 親アプリケーションに楽曲情報を適用
        this.parentApp.applyMusicMetadata(this.musicAssignments);
        this.close();
    }

    close() {
        const dialog = document.getElementById('musicMetadataDialog');
        if (dialog) {
            dialog.remove();
        }
    }
}

// CSS追加
const metadataEditorCSS = `
.metadata-dialog {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1000;
}

.metadata-dialog-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
}

.metadata-dialog-content {
    background: white;
    border-radius: 8px;
    width: 90%;
    max-width: 800px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.metadata-dialog-header {
    padding: 20px;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.metadata-dialog-header h3 {
    margin: 0;
    color: #333;
}

.close-dialog {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #666;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.close-dialog:hover {
    color: #333;
    background: #f0f0f0;
    border-radius: 50%;
}

.metadata-dialog-body {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
}

.music-assignment-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.assignment-item {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background: #f9f9f9;
}

.assignment-header {
    margin-bottom: 15px;
    color: #555;
    font-weight: bold;
}

.assignment-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
}

.field-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.field-group label {
    font-weight: bold;
    color: #333;
    font-size: 14px;
}

.field-group input,
.field-group select,
.field-group textarea {
    padding: 8px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 14px;
}

.field-group textarea {
    resize: vertical;
    min-height: 50px;
}

.metadata-dialog-footer {
    padding: 20px;
    border-top: 1px solid #eee;
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

.btn-primary {
    background: #007bff;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.btn-primary:hover {
    background: #0056b3;
}

.btn-secondary {
    background: #6c757d;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.btn-secondary:hover {
    background: #5a6268;
}

@media (max-width: 768px) {
    .assignment-fields {
        grid-template-columns: 1fr;
    }
    
    .metadata-dialog-content {
        width: 95%;
        max-height: 90vh;
    }
}
`;

// CSSを動的に追加
const styleElement = document.createElement('style');
styleElement.textContent = metadataEditorCSS;
document.head.appendChild(styleElement);
