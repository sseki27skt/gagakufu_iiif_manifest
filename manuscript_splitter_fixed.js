class ManuscriptSplitter {
    constructor() {
        this.currentManifest = null;
        this.currentManifestPath = null;
        this.markedPages = new Map();
        this.canvases = [];
        this.baseUrl = window.location.origin + window.location.pathname.replace('manuscript_splitter.html', '');
        this.musicMetadata = null;
        
        this.initializeEventListeners();
        this.setupInitialState();
        this.loadMusicMetadata();
    }

    initializeEventListeners() {
        document.getElementById('manifestSource').addEventListener('change', (e) => {
            this.toggleManifestSource(e.target.value);
        });

        document.getElementById('collectionSelect').addEventListener('change', (e) => {
            console.log('Collection changed to:', e.target.value);
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

        // コピーボタンがあれば追加
        const copyButton = document.getElementById('copyCommand');
        if (copyButton) {
            copyButton.addEventListener('click', () => {
                this.copyCommandToClipboard();
            });
        }
    }

    setupInitialState() {
        console.log('Setting up initial state');
        document.getElementById('manifestSource').value = 'collection';
        this.toggleManifestSource('collection');
        this.loadVolumeOptions();
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
    }

    async loadVolumeOptions() {
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

        console.log('Enabling volume select and loading volume labels...');
        volumeSelect.disabled = false;
        volumeSelect.innerHTML = '<option value="" class="loading-volumes">📚 巻一覧を読み込み中...</option>';

        try {
            // インデックスファイルから巻一覧とlabelを取得
            const volumes = await this.loadVolumesFromIndex(collectionSelect.value);
            
            volumeSelect.innerHTML = '<option value="">選択してください</option>';
            
            volumes.forEach(volume => {
                const option = document.createElement('option');
                option.value = volume.filename;
                option.textContent = volume.displayName;
                volumeSelect.appendChild(option);
            });
            
            console.log(`${volumes.length} volumes loaded from index`);
        } catch (error) {
            console.error('Error loading volumes from index:', error);
            // フォールバック: 従来の方法で巻を検索
            console.log('Falling back to volume discovery...');
            await this.fallbackVolumeDiscovery(collectionSelect.value, volumeSelect);
        }
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

    async loadManifest() {
        const manifestSource = document.getElementById('manifestSource').value;
        
        if (manifestSource === 'local') {
            this.showMessage('ローカルファイルが既に選択されています。', 'info');
            return;
        }

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
            this.currentManifestPath = `${collection}/${volume}`;
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

        // 遅延読み込みを初期化
        this.initializeLazyLoading();
    }

    initializeLazyLoading() {
        // Intersection Observer で画像の遅延読み込み
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    const src = img.dataset.src;
                    if (src) {
                        img.src = src;
                        img.removeAttribute('data-src');
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                }
            });
        }, {
            rootMargin: '50px' // 50px前に読み込み開始
        });

        // 遅延読み込み対象の画像を監視
        document.querySelectorAll('img.lazy').forEach(img => {
            imageObserver.observe(img);
        });
    }

    createImageItem(canvas, index) {
        const item = document.createElement('div');
        item.className = 'image-item';
        item.dataset.pageIndex = index;

        const thumbnailUrl = this.getThumbnailUrl(canvas);
        const fullUrl = this.getFullImageUrl(canvas);
        
        item.innerHTML = `
            <div class="image-container">
                <img data-src="${thumbnailUrl}" alt="Page ${index + 1}" class="thumbnail-image lazy" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect width='100%25' height='100%25' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999'%3E読み込み中...%3C/text%3E%3C/svg%3E" />
                <div class="image-overlay">
                    <button class="view-full-btn" title="フルサイズで表示">🔍</button>
                </div>
            </div>
            <div class="image-info">
                <div class="image-label">ページ ${index + 1}</div>
                <div class="title-count">
                    <label>タイトル数:</label>
                    <input type="number" min="0" max="10" value="0" class="title-count-input" />
                </div>
            </div>
        `;

        // クリックイベント（タイトルページマーキング）
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('title-count-input') || 
                e.target.classList.contains('view-full-btn')) {
                return;
            }
            this.togglePageMark(index);
        });

        // フルサイズ表示ボタン
        const viewFullBtn = item.querySelector('.view-full-btn');
        viewFullBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showFullSizeImage(fullUrl, index + 1);
        });

        // タイトル数入力
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

    getImageUrl(canvas, size = 'thumbnail') {
        if (canvas.images && canvas.images[0] && canvas.images[0].resource) {
            const fullUrl = canvas.images[0].resource['@id'];
            
            // IIIFのservice情報を確認
            const service = canvas.images[0].resource.service;
            if (service && service['@id']) {
                // IIIF Image API を使用してサムネイル取得
                const serviceUrl = service['@id'];
                
                switch (size) {
                    case 'thumbnail':
                        // 最大幅400px、品質default（縦横比保持）
                        return `${serviceUrl}/full/!400,400/0/default.jpg`;
                    case 'medium':
                        // 最大幅800px
                        return `${serviceUrl}/full/!800,800/0/default.jpg`;
                    case 'full':
                        // フルサイズ
                        return `${serviceUrl}/full/full/0/default.jpg`;
                    default:
                        return fullUrl;
                }
            }
            
            // フォールバック: 元のURL
            return fullUrl;
        }
        return '';
    }

    getThumbnailUrl(canvas) {
        return this.getImageUrl(canvas, 'thumbnail');
    }

    getFullImageUrl(canvas) {
        return this.getImageUrl(canvas, 'full');
    }

    showFullSizeImage(imageUrl, pageNumber) {
        // 既存のモーダルがあれば削除
        const existingModal = document.getElementById('imageModal');
        if (existingModal) {
            existingModal.remove();
        }

        // モーダルを作成
        const modal = document.createElement('div');
        modal.id = 'imageModal';
        modal.className = 'image-modal';
        modal.innerHTML = `
            <div class="image-modal-overlay">
                <div class="image-modal-content">
                    <div class="image-modal-header">
                        <h3>ページ ${pageNumber} - フルサイズ表示</h3>
                        <button class="close-modal" type="button">×</button>
                    </div>
                    <div class="image-modal-body">
                        <div class="loading-indicator">読み込み中...</div>
                        <img src="${imageUrl}" alt="ページ ${pageNumber}" class="full-size-image" style="display: none;" />
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // イベントリスナー
        const closeBtn = modal.querySelector('.close-modal');
        const overlay = modal.querySelector('.image-modal-overlay');
        const fullImage = modal.querySelector('.full-size-image');
        const loadingIndicator = modal.querySelector('.loading-indicator');

        // 閉じるボタン
        closeBtn.addEventListener('click', () => {
            modal.remove();
        });

        // オーバーレイクリックで閉じる
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                modal.remove();
            }
        });

        // ESCキーで閉じる
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);

        // 画像読み込み完了時
        fullImage.addEventListener('load', () => {
            loadingIndicator.style.display = 'none';
            fullImage.style.display = 'block';
        });

        // 画像読み込み失敗時
        fullImage.addEventListener('error', () => {
            loadingIndicator.textContent = '画像の読み込みに失敗しました';
        });
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
        
        document.getElementById('titlePagesFile').textContent = `タイトルページ情報: ${filename}`;
        
        this.showMessage(`タイトルページ情報をエクスポートしました: ${filename}`, 'success');
    }

    generateTitlePagesFilename() {
        const manifestName = this.currentManifestPath ? 
            this.currentManifestPath.replace('.json', '').replace('/', '_') : 
            `${this.getCurrentCollection()}_${document.getElementById('volumeSelect').value.replace('.json', '')}`;
        
        return `${manifestName}_title_pages.json`;
    }

    getCurrentManifestPath() {
        const collection = this.getCurrentCollection();
        const volume = document.getElementById('volumeSelect').value;
        return collection && volume ? `${collection}/${volume}` : '';
    }

    getCurrentCollection() {
        const collectionSelect = document.getElementById('collectionSelect');
        return collectionSelect.value;
    }

    showPythonCommand() {
        if (this.markedPages.size === 0) {
            this.showMessage('まずタイトルページをマークしてください。', 'error');
            return;
        }

        const manifestPath = this.currentManifestPath || this.getCurrentManifestPath();
        const titlePagesFile = this.generateTitlePagesFilename();
        
        // 雅楽メタデータを含むコマンドを生成
        const command = `python3 iiif_manifest_splitter.py "${manifestPath}" "${titlePagesFile}" -g gagaku_titles_metadata.json -m music_metadata.json`;
        
        document.getElementById('pythonCommand').textContent = command;
        document.getElementById('pythonCommandSection').style.display = 'block';
        
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
        document.getElementById('pythonCommandSection').style.display = 'none';
    }

    clearData() {
        this.currentManifest = null;
        this.currentManifestPath = null;
        this.canvases = [];
        this.clearMarks();
        document.getElementById('imageGrid').innerHTML = '';
        document.getElementById('pythonCommandSection').style.display = 'none';
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

    async loadVolumesFromIndex(collection) {
        const indexUrl = `${this.baseUrl}${collection}/manifest-index.json`;
        const response = await fetch(indexUrl);
        
        if (!response.ok) {
            throw new Error(`Index file not found: ${response.status}`);
        }
        
        const indexData = await response.json();
        const volumes = [];
        
        if (indexData.manifests) {
            indexData.manifests.forEach((manifest, index) => {
                // URLからファイル名を抽出
                const url = manifest['@id'];
                const filename = url.substring(url.lastIndexOf('/') + 1);
                
                // 巻番号を抽出（volume数字_manifest.json）
                const volumeMatch = filename.match(/volume(\d+)_manifest\.json/);
                const volumeNumber = volumeMatch ? parseInt(volumeMatch[1]) : index;
                
                volumes.push({
                    filename: filename,
                    volumeNumber: volumeNumber,
                    displayName: `巻${volumeNumber.toString().padStart(2, '0')}: ${manifest.label}`,
                    label: manifest.label
                });
            });
        }
        
        return volumes.sort((a, b) => a.volumeNumber - b.volumeNumber);
    }

    async fallbackVolumeDiscovery(collection, volumeSelect) {
        try {
            const volumes = await this.discoverVolumes(collection);
            
            volumeSelect.innerHTML = '<option value="">選択してください</option>';
            
            volumes.forEach(volume => {
                const option = document.createElement('option');
                option.value = volume.filename;
                option.textContent = volume.displayName;
                volumeSelect.appendChild(option);
            });
            
            console.log(`${volumes.length} volumes loaded via discovery`);
        } catch (error) {
            console.error('Fallback discovery also failed:', error);
            volumeSelect.innerHTML = '<option value="">エラー: 巻の読み込みに失敗</option>';
        }
    }

    async discoverVolumes(collection) {
        const volumes = [];
        const maxVolumes = 100; // 最大100巻まで検索
        
        // 並列で複数の巻をチェック（パフォーマンス向上）
        const promises = [];
        for (let i = 0; i <= maxVolumes; i++) {
            const filename = `volume${i}_manifest.json`;
            promises.push(this.checkVolumeExists(collection, filename, i));
        }
        
        // 5つずつ並列処理（サーバー負荷を考慮）
        const batchSize = 5;
        for (let i = 0; i < promises.length; i += batchSize) {
            const batch = promises.slice(i, i + batchSize);
            const results = await Promise.allSettled(batch);
            
            results.forEach(result => {
                if (result.status === 'fulfilled' && result.value) {
                    volumes.push(result.value);
                }
            });
        }
        
        return volumes.sort((a, b) => a.volumeNumber - b.volumeNumber);
    }

    async checkVolumeExists(collection, filename, volumeNumber) {
        try {
            const manifestUrl = `${this.baseUrl}${collection}/${filename}`;
            const response = await fetch(manifestUrl, { method: 'HEAD' });
            
            if (response.ok) {
                // ファイルが存在する場合、labelを取得
                const manifestResponse = await fetch(manifestUrl);
                if (manifestResponse.ok) {
                    const manifest = await manifestResponse.json();
                    const label = manifest.label || `Volume ${volumeNumber}`;
                    return {
                        filename: filename,
                        volumeNumber: volumeNumber,
                        displayName: `巻${volumeNumber.toString().padStart(2, '0')}: ${label}`,
                        label: label
                    };
                }
            }
            return null;
        } catch (error) {
            // エラーは無視（ファイルが存在しない場合）
            return null;
        }
    }
}

// アプリケーションを初期化
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing ManuscriptSplitter');
    new ManuscriptSplitter();
});
