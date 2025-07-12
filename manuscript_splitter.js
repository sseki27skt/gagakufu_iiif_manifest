class ManuscriptSplitter {
    constructor() {
        this.currentManifest = null;
        this.currentManifestPath = null;
        this.markedPages = new Map(); // pageIndex -> titleCount
        this.canvases = [];
        this.baseUrl = window.location.origin + window.location.pathname.replace('manuscript_splitter.html', '');
        this.musicMetadata = null;
        this.userMusicAssignments = new Map(); // splitIndex -> musicInfo
        
        this.initializeEventListeners();
        this.setupInitialState();
        this.loadMusicMetadata();
    }

    setupInitialState() {
        console.log('Setting up initial state');
        // 初期状態では既存コレクションを選択状態にする
        document.getElementById('manifestSource').value = 'collection';
        this.toggleManifestSource('collection');
        this.loadVolumeOptions();
    }

    initializeEventListeners() {
        document.getElementById('manifestSource').addEventListener('change', (e) => {
            this.toggleManifestSource(e.target.value);
        });

        document.getElementById('collectionSelect').addEventListener('change', (e) => {
            this.loadVolumeOptions();
            this.clearData();
        });

        document.getElementById('manifestFile').addEventListener('change', (e) => {
            this.handleLocalFileSelection(e.target.files[0]);
        });

        document.getElementById('loadManifest').addEventListener('click', () => {
            this.loadManifest();
        });

        document.getElementById('clearMarks').addEventListener('click', () => {
            this.clearMarks();
        });

        document.getElementById('exportTitlePages').addEventListener('click', () => {
            this.exportTitlePages();
        });

        document.getElementById('showPythonCommand').addEventListener('click', () => {
            this.showPythonCommand();
        });

        document.getElementById('copyCommand').addEventListener('click', () => {
            this.copyCommandToClipboard();
        });
    }

    async loadMusicMetadata() {
        try {
            const response = await fetch(`${this.baseUrl}music_metadata.json`);
            if (response.ok) {
                this.musicMetadata = await response.json();
            }
        } catch (error) {
            console.warn('Music metadata not loaded:', error);
        }
    loadVolumeOptions() {
        console.log('loadVolumeOptions called');
        const collectionSelect = document.getElementById('collectionSelect');
        const volumeSelect = document.getElementById('volumeSelect');
        
        console.log('Collection value:', collectionSelect.value);
        
        if (!collectionSelect.value) {
            volumeSelect.innerHTML = '<option value="">まずコレクションを選択してください</option>';
            volumeSelect.disabled = true;
            console.log('Volume select disabled');
            return;
        }

        console.log('Enabling volume select');
        volumeSelect.disabled = false;
        volumeSelect.innerHTML = '<option value="">選択してください</option>';

        // 動的にボリュームリストを生成（0から100まで）
        for (let i = 0; i <= 100; i++) {
            const option = document.createElement('option');
            option.value = `volume${i}_manifest.json`;
            option.textContent = `Volume ${i}`;
            volumeSelect.appendChild(option);
        }
        console.log('Volume options loaded');
    }

    async loadManifest() {
        const collection = document.getElementById('collectionSelect').value;
        const volume = document.getElementById('volumeSelect').value;

        if (!collection || !volume) {
            this.showMessage('コレクションと巻を選択してください。', 'error');
            return;
        }

        try {
            this.showLoading(true);
            this.clearData();

            const manifestUrl = `${this.baseUrl}${collection}/${volume}`;
            const response = await fetch(manifestUrl);
            
            if (!response.ok) {
                throw new Error(`マニフェストの読み込みに失敗しました: ${response.status}`);
            }

            this.currentManifest = await response.json();
            this.extractCanvases();
            this.renderImages();
            this.showMessage('マニフェストを正常に読み込みました。', 'success');

        } catch (error) {
            console.error('Error loading manifest:', error);
            this.showMessage(`エラー: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    extractCanvases() {
        this.canvases = [];
        if (this.currentManifest && this.currentManifest.sequences && this.currentManifest.sequences[0]) {
            this.canvases = this.currentManifest.sequences[0].canvases || [];
        }
    }

    renderImages() {
        const imageGrid = document.getElementById('imageGrid');
        imageGrid.innerHTML = '';

        this.canvases.forEach((canvas, index) => {
            const imageItem = this.createImageItem(canvas, index);
            imageGrid.appendChild(imageItem);
        });
    }

    createImageItem(canvas, index) {
        const item = document.createElement('div');
        item.className = 'image-item';
        item.dataset.pageIndex = index;

        // 画像URLを取得
        const imageUrl = this.getImageUrl(canvas);
        
        item.innerHTML = `
            <img src="${imageUrl}" alt="Page ${index + 1}" loading="lazy" />
            <div class="image-info">
                <div class="image-label">ページ ${index + 1}</div>
                <div class="title-count">
                    <label>タイトル数:</label>
                    <input type="number" min="0" max="10" value="0" class="title-count-input" />
                </div>
            </div>
        `;

        // クリックイベント
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('title-count-input')) {
                return; // 入力フィールドのクリックは無視
            }
            this.togglePageMark(index);
        });

        // 入力フィールドの変更イベント
        const input = item.querySelector('.title-count-input');
        input.addEventListener('change', (e) => {
            const titleCount = parseInt(e.target.value) || 0;
            if (titleCount > 0) {
                this.markPage(index, titleCount);
            } else {
                this.unmarkPage(index);
            }
        });

        return item;
    }

    getImageUrl(canvas) {
        if (canvas.images && canvas.images[0] && canvas.images[0].resource) {
            return canvas.images[0].resource['@id'];
        }
        return '';
    }

    togglePageMark(pageIndex) {
        if (this.markedPages.has(pageIndex)) {
            this.unmarkPage(pageIndex);
        } else {
            this.markPage(pageIndex, 1);
        }
    }

    markPage(pageIndex, titleCount) {
        this.markedPages.set(pageIndex, titleCount);
        this.updatePageDisplay(pageIndex);
        this.updateMarkedPagesDisplay();
        this.updateGenerateButton();
    }

    unmarkPage(pageIndex) {
        this.markedPages.delete(pageIndex);
        this.updatePageDisplay(pageIndex);
        this.updateMarkedPagesDisplay();
        this.updateGenerateButton();
    }

    updatePageDisplay(pageIndex) {
        const item = document.querySelector(`[data-page-index="${pageIndex}"]`);
        const input = item.querySelector('.title-count-input');
        
        if (this.markedPages.has(pageIndex)) {
            item.classList.add('marked');
            input.value = this.markedPages.get(pageIndex);
        } else {
            item.classList.remove('marked');
            input.value = 0;
        }
    }

    updateMarkedPagesDisplay() {
        const display = document.getElementById('markedPagesDisplay');
        const list = document.getElementById('markedPagesList');

        if (this.markedPages.size === 0) {
            display.style.display = 'none';
            return;
        }

        display.style.display = 'block';
        list.innerHTML = '';

        // ページ番号順にソート
        const sortedPages = Array.from(this.markedPages.entries()).sort((a, b) => a[0] - b[0]);
        
        sortedPages.forEach(([pageIndex, titleCount]) => {
            const chip = document.createElement('span');
            chip.className = 'page-chip';
            chip.textContent = `ページ ${pageIndex + 1} (${titleCount}曲)`;
            list.appendChild(chip);
        });
    }

    updateGenerateButton() {
        const showPythonButton = document.getElementById('showPythonCommand');
        const hasMarkedPages = this.markedPages.size > 0;
        
        showPythonButton.disabled = !hasMarkedPages;
    }

    toggleManifestSource(source) {
        const collectionControls = document.getElementById('collectionControls');
        const localFileControls = document.getElementById('localFileControls');
        
        if (source === 'local') {
            collectionControls.style.display = 'none';
            localFileControls.style.display = 'flex';
        } else {
            collectionControls.style.display = 'flex';
            localFileControls.style.display = 'none';
            // 既存コレクションに戻った場合は巻選択を更新
            this.loadVolumeOptions();
        }
        
        this.clearData();
    }

    handleLocalFileSelection(file) {
        if (file && file.type === 'application/json') {
            this.currentManifestPath = file.name;
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    this.currentManifest = JSON.parse(e.target.result);
                    this.extractCanvases();
                    this.renderImages();
                    this.showMessage('ローカルマニフェストを正常に読み込みました。', 'success');
                } catch (error) {
                    this.showMessage(`マニフェストの解析に失敗しました: ${error.message}`, 'error');
                }
            };
            reader.readAsText(file);
        } else {
            this.showMessage('JSONファイルを選択してください。', 'error');
        }
    }

    exportTitlePages() {
        if (this.markedPages.size === 0) {
            this.showMessage('マークされたページがありません。', 'error');
            return;
        }

        const titlePagesData = {
            manifest_file: this.currentManifestPath || this.getCurrentManifestPath(),
            export_date: new Date().toISOString(),
            title_pages: Array.from(this.markedPages.entries()).map(([pageIndex, titleCount]) => ({
                page: pageIndex,
                titles: titleCount
            })).sort((a, b) => a.page - b.page)
        };

        const filename = this.generateTitlePagesFilename();
        this.downloadJson(titlePagesData, filename);
        
        // ファイル情報を更新
        document.getElementById('titlePagesFile').textContent = `タイトルページ情報: ${filename}`;
        
        this.showMessage(`タイトルページ情報をエクスポートしました: ${filename}`, 'success');
    }

    generateTitlePagesFilename() {
        const manifestName = this.currentManifestPath ? 
            this.currentManifestPath.replace('.json', '') : 
            `${this.getCurrentCollection()}_${document.getElementById('volumeSelect').value.replace('.json', '')}`;
        
        return `${manifestName}_title_pages.json`;
    }

    getCurrentManifestPath() {
        const collection = this.getCurrentCollection();
        const volume = document.getElementById('volumeSelect').value;
        return collection && volume ? `${collection}/${volume}` : '';
    }

    showPythonCommand() {
        if (this.markedPages.size === 0) {
            this.showMessage('まずタイトルページをマークしてください。', 'error');
            return;
        }

        const manifestPath = this.currentManifestPath || this.getCurrentManifestPath();
        const titlePagesFile = this.generateTitlePagesFilename();
        
        const command = `python3 iiif_manifest_splitter.py "${manifestPath}" "${titlePagesFile}" -m music_metadata.json`;
        
        document.getElementById('pythonCommand').textContent = command;
        document.getElementById('pythonCommandSection').style.display = 'block';
        
        // ページをスクロール
        document.getElementById('pythonCommandSection').scrollIntoView({ behavior: 'smooth' });
    }

    copyCommandToClipboard() {
        const command = document.getElementById('pythonCommand').textContent;
        navigator.clipboard.writeText(command).then(() => {
            this.showMessage('コマンドをクリップボードにコピーしました。', 'success');
        }).catch(() => {
            this.showMessage('コピーに失敗しました。手動でコマンドをコピーしてください。', 'error');
        });
    }

    clearMarks() {
        this.markedPages.clear();
        document.querySelectorAll('.image-item').forEach(item => {
            item.classList.remove('marked');
            item.querySelector('.title-count-input').value = 0;
        });
        this.updateMarkedPagesDisplay();
        this.updateGenerateButton();
        document.getElementById('generationSection').style.display = 'none';
    }

    clearData() {
        this.currentManifest = null;
        this.currentManifestPath = null;
        this.canvases = [];
        this.clearMarks();
        document.getElementById('imageGrid').innerHTML = '';
        document.getElementById('pythonCommandSection').style.display = 'none';
    }

    getCurrentCollection() {
        const collectionSelect = document.getElementById('collectionSelect');
        return collectionSelect.value;
    }

    downloadJson(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    showMessage(message, type) {
        const messageArea = document.getElementById('messageArea');
        messageArea.innerHTML = `<div class="${type}">${message}</div>`;
        setTimeout(() => {
            messageArea.innerHTML = '';
        }, 5000);
    }

    showLoading(show) {
        document.getElementById('loadingArea').style.display = show ? 'block' : 'none';
    }
}

// アプリケーションを初期化
document.addEventListener('DOMContentLoaded', () => {
    new ManuscriptSplitter();
});
