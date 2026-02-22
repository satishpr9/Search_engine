document.addEventListener('DOMContentLoaded', () => {

    // Core DOM Elements
    const app = document.getElementById('app');
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const clearBtn = document.getElementById('clear-btn');
    const homeBtn = document.getElementById('home-btn');

    const statsBadge = document.getElementById('stats-badge');
    const statsText = document.getElementById('stats-text');

    // Results DOM
    const loader = document.getElementById('loader');
    const resultsList = document.getElementById('results-list');
    const resultsMeta = document.getElementById('results-meta');
    const zeroState = document.getElementById('zero-state');
    const instantWidget = document.getElementById('instant-widget');
    const aiOverview = document.getElementById('ai-overview');
    const aiSummaryText = document.getElementById('ai-summary-text');
    const aiShowMore = document.getElementById('ai-show-more');
    const imageCarousel = document.getElementById('image-carousel');
    const knowledgePanel = document.getElementById('knowledge-panel');
    const aiChatThread = document.getElementById('ai-chat-thread');
    const aiChatForm = document.getElementById('ai-chat-form');
    const aiChatInput = document.getElementById('ai-chat-input');

    // Search Tabs DOM
    const searchTabsContainer = document.getElementById('search-tabs');
    const searchTabs = document.querySelectorAll('.search-tab');

    // Show More Action
    aiShowMore.addEventListener('click', () => {
        aiSummaryText.classList.toggle('expanded');
        if (aiSummaryText.classList.contains('expanded')) {
            aiShowMore.style.display = 'none';
            aiChatForm.style.display = 'flex';
            aiChatInput.focus();
        }
    });

    // Chat Submit Action
    aiChatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const followUp = aiChatInput.value.trim();
        if (!followUp || !searchContextStr) return;

        // Render user question bubble
        const userBubble = document.createElement('div');
        userBubble.className = 'chat-bubble user';
        userBubble.textContent = followUp;
        aiChatThread.appendChild(userBubble);

        aiChatInput.value = '';
        aiChatInput.disabled = true;

        // Render empty AI bubble to fill
        const aiBubble = document.createElement('div');
        aiBubble.className = 'chat-bubble ai';
        aiBubble.innerHTML = '<div class="nexus-spinner" style="width: 14px; height: 14px; border-width: 2px;"></div>';
        aiChatThread.appendChild(aiBubble);

        streamChatFollowUp(followUp, searchContextStr, aiHistoryStr, aiBubble);
    });

    // Advanced UI DOM
    const autocompleteBox = document.getElementById('autocomplete-box');
    const spellCorrection = document.getElementById('spell-correction');
    const correctionLink = document.getElementById('correction-link');

    // Pagination DOM
    const pagination = document.getElementById('pagination');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const pageNumbers = document.getElementById('page-numbers');

    // Crawler DOM
    const fabCrawl = document.getElementById('fab-crawl');
    const crawlModal = document.getElementById('crawl-modal');
    const closeModal = document.getElementById('close-modal');
    const crawlForm = document.getElementById('crawl-form');
    const crawlInput = document.getElementById('crawl-input');
    const crawlStatus = document.getElementById('crawl-status');

    // State
    const API_BASE = '/api';
    let currentQuery = '';
    let currentPage = 1;
    let currentSearchType = 'all';
    let debounceTimer = null;

    // --- On Load ---
    app.classList.add('state-home');
    fetchStats();

    // --- Event Listeners ---

    // Click Home Logo
    homeBtn.addEventListener('click', () => {
        resetToHome();
    });

    // Handle Search Submission
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (!query) return;

        autocompleteBox.classList.remove('active');
        executeSearch(query, 1);
    });

    // Clear Button logic
    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        autocompleteBox.classList.remove('active');
        searchInput.focus();
    });

    // Autocomplete Input Listener
    searchInput.addEventListener('input', (e) => {
        const val = e.target.value;

        if (val.length > 0) {
            clearBtn.style.display = 'block';

            // Debounce the suggest API calls to prevent flooding the backend
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                fetchSuggestions(val.trim());
            }, 150);
        } else {
            clearBtn.style.display = 'none';
            autocompleteBox.classList.remove('active');
        }
    });

    // Close autocomplete when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchForm.contains(e.target) && !autocompleteBox.contains(e.target)) {
            autocompleteBox.classList.remove('active');
        }
    });

    // Did You Mean Click
    correctionLink.addEventListener('click', (e) => {
        e.preventDefault();
        const correctQuery = e.target.textContent;
        searchInput.value = correctQuery;
        executeSearch(correctQuery, 1);
    });

    // Search Tabs Click
    searchTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            searchTabs.forEach(t => t.classList.remove('active'));
            e.currentTarget.classList.add('active');
            currentSearchType = e.currentTarget.dataset.type;

            if (currentSearchType === 'all') {
                app.classList.remove('state-full-width');
            } else {
                app.classList.add('state-full-width');
            }

            if (searchInput.value.trim() !== '') {
                executeSearch(searchInput.value.trim(), 1);
            }
        });
    });

    // Pagination Listeners
    prevBtn.addEventListener('click', () => { if (currentPage > 1) executeSearch(currentQuery, currentPage - 1); });
    nextBtn.addEventListener('click', () => { executeSearch(currentQuery, currentPage + 1); });

    // Crawl Modal Listeners
    fabCrawl.addEventListener('click', () => {
        crawlModal.classList.add('active');
        crawlInput.focus();
    });

    closeModal.addEventListener('click', () => {
        crawlModal.classList.remove('active');
        crawlStatus.style.display = 'none';
        crawlInput.value = '';
    });

    crawlModal.addEventListener('click', (e) => {
        if (e.target === crawlModal) closeModal.click();
    });

    crawlForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = crawlInput.value.trim();
        if (!url) return;

        const btn = crawlForm.querySelector('.crawl-submit-btn');
        btn.disabled = true;
        btn.innerHTML = `<div class="nexus-spinner" style="width: 20px; height: 20px; border-width: 2px;"></div>`;
        crawlStatus.style.display = 'block';
        crawlStatus.style.color = 'var(--text-muted)';
        crawlStatus.textContent = 'Starting crawl...';

        try {
            const res = await fetch(`${API_BASE}/crawl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            if (res.ok) {
                crawlStatus.style.color = 'var(--url-color)';
                crawlStatus.textContent = 'Crawler dispatched! Page and its links will be indexed shortly.';
                setTimeout(() => closeModal.click(), 3000);
            } else {
                throw new Error('Failed');
            }
        } catch (error) {
            crawlStatus.style.color = '#f85149';
            crawlStatus.textContent = 'Error: Could not start the crawler.';
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<span>Crawl</span> <i class="ph ph-arrow-right"></i>`;
        }
    });

    // --- Core Methods ---

    function resetToHome() {
        app.classList.remove('state-searched');
        app.classList.add('state-home');
        app.classList.remove('state-full-width');
        searchInput.value = '';
        clearBtn.style.display = 'none';
        resultsList.innerHTML = '';
        resultsMeta.style.display = 'none';
        aiOverview.style.display = 'none';
        aiShowMore.style.display = 'none';
        imageCarousel.style.display = 'none';
        imageCarousel.innerHTML = '';
        knowledgePanel.style.display = 'none';
        spellCorrection.style.display = 'none';
        pagination.style.display = 'none';
        searchTabsContainer.style.display = 'none';
        zeroState.style.display = 'flex';
        autocompleteBox.classList.remove('active');
        currentQuery = '';
    }

    async function fetchStats() {
        try {
            const res = await fetch(`${API_BASE}/stats`);
            if (res.ok) {
                const data = await res.json();
                statsText.textContent = `${data.indexed_pages} Articles • ${data.discovered_links} Links`;
            } else {
                statsBadge.style.display = 'none';
            }
        } catch (e) {
            statsBadge.style.display = 'none';
        }
    }

    async function fetchSuggestions(query) {
        if (!query || query.length < 2) return;
        try {
            const res = await fetch(`${API_BASE}/suggest?q=${encodeURIComponent(query)}`);
            if (res.ok) {
                const suggs = await res.json();
                renderSuggestions(suggs);
            }
        } catch (e) { }
    }

    function renderSuggestions(suggestions) {
        if (suggestions.length === 0) {
            autocompleteBox.classList.remove('active');
            return;
        }

        const html = suggestions.map(s => `
            <div class="suggestion-item">
                <i class="ph ph-magnifying-glass"></i>
                <span>${s}</span>
            </div>
        `).join('');

        autocompleteBox.innerHTML = html;
        autocompleteBox.classList.add('active');

        // Click a suggestion to search
        const items = autocompleteBox.querySelectorAll('.suggestion-item');
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                const text = e.currentTarget.querySelector('span').textContent;
                searchInput.value = text;
                autocompleteBox.classList.remove('active');
                executeSearch(text, 1);
            });
        });
    }

    async function executeSearch(query, page) {
        currentQuery = query;
        currentPage = page;

        // Transition Layout Frame
        if (app.classList.contains('state-home')) {
            app.classList.remove('state-home');
            app.classList.add('state-searched');
            zeroState.style.display = 'none';
            await new Promise(r => setTimeout(r, 200)); // wait for upward sweep transition
        }

        // Setup Loading UI State
        searchForm.classList.add('focused');
        resultsList.innerHTML = '';
        instantWidget.style.display = 'none';
        resultsMeta.style.display = 'none';
        aiOverview.style.display = 'none';
        aiShowMore.style.display = 'none';
        aiChatForm.style.display = 'none';
        aiChatThread.innerHTML = '';
        searchContextStr = '';
        aiHistoryStr = '';
        imageCarousel.style.display = 'none';
        imageCarousel.innerHTML = '';
        knowledgePanel.style.display = 'none';
        spellCorrection.style.display = 'none';
        pagination.style.display = 'none';
        searchTabsContainer.style.display = 'flex';
        loader.style.display = 'flex';

        try {
            const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&page=${page}&type=${currentSearchType}`);
            if (!res.ok) throw new Error("Search failed");

            const data = await res.json();
            renderResults(data);
        } catch (error) {
            loader.style.display = 'none';
            searchForm.classList.remove('focused');
            resultsList.innerHTML = `
                <div class="result-card" style="text-align:center; padding: 40px 0;">
                    <i class="ph-duotone ph-warning-circle" style="font-size: 3rem; color: #f85149; margin-bottom: 16px;"></i>
                    <p style="color: var(--text-muted);">Failed to query the search index.</p>
                </div>
            `;
        }
    }

    function renderResults(data) {
        loader.style.display = 'none';
        searchForm.classList.remove('focused');

        // 1. Did You Mean
        if (data.did_you_mean) {
            correctionLink.textContent = data.did_you_mean;
            spellCorrection.style.display = 'flex';
        }

        // 2. Empty Results Handling
        if (data.results.length === 0) {
            resultsList.innerHTML = `
                <div class="result-card" style="padding: 20px;">
                    <p style="font-size: 1.1rem; margin-bottom: 12px;">No results found for <strong>${data.query}</strong>.</p>
                    <p style="color: var(--text-muted);">Try checking for spelling errors, using fewer keywords, or trying more general terms.</p>
                </div>
            `;
            return;
        }

        // 3. Render Metadata
        const seconds = (data.total_time_ms / 1000).toFixed(3);
        resultsMeta.innerHTML = `<i class="ph ph-lightning"></i> Found ${data.total_hits} results in ${seconds}s`;
        resultsMeta.style.display = 'block';

        // 3.2 Render Instant Widget
        if (data.widget) {
            if (data.widget.type === 'calculator') {
                instantWidget.innerHTML = `
                    <div class="widget-calc-expr">${data.widget.expression} =</div>
                    <div class="widget-calc-res">${data.widget.result}</div>
                `;
                instantWidget.style.display = 'block';
            } else if (data.widget.type === 'weather') {
                let iconClass = 'ph-sun';
                if (data.widget.condition.includes('Rain') || data.widget.condition.includes('Drizzle')) iconClass = 'ph-cloud-rain';
                else if (data.widget.condition.includes('Cloud')) iconClass = 'ph-cloud';
                else if (data.widget.condition.includes('Snow')) iconClass = 'ph-snowflake';
                else if (data.widget.condition.includes('Thunder')) iconClass = 'ph-cloud-lightning';
                else if (data.widget.condition.includes('Fog')) iconClass = 'ph-cloud-fog';

                instantWidget.innerHTML = `
                    <div class="widget-weather-header">
                        <i class="ph-fill ${iconClass} widget-weather-icon"></i>
                        <div class="widget-weather-temp">${data.widget.temperature}</div>
                        <div class="widget-weather-details">
                            <div class="widget-weather-cond">${data.widget.condition}</div>
                            <div class="widget-weather-loc">${data.widget.location}</div>
                        </div>
                    </div>
                `;
                instantWidget.style.display = 'block';
            }
        }

        // 3.5. Render AI Summary via SSE Stream (Only on 'All' tab)
        if (currentSearchType === 'all' && data.results && data.results.length > 0) {
            aiSummaryText.innerHTML = '<div class="nexus-spinner" style="width: 20px; height: 20px; border-width: 2px;"></div>';
            aiOverview.style.display = 'flex';
            aiSummaryText.classList.remove('expanded');
            aiShowMore.style.display = 'none';
            aiShowMore.innerHTML = `<i class="ph ph-caret-down"></i> Show more`;

            const contextText = data.results.slice(0, 5).map(r => `Title: ${r.title}\nSnippet: ${r.snippet}`).join('\n\n');
            searchContextStr = contextText;
            streamAiSummary(data.query, contextText);
        }

        // 3.6 Render News Carousel (Only on 'All' tab)
        if (currentSearchType === 'all' && data.image_results && data.image_results.length > 0) {
            let imgHTML = '';
            data.image_results.forEach(img => {
                let domain = "source";
                try { domain = new URL(img.url).hostname.replace('www.',''); } catch(e){}
                imgHTML += `
                    <a href="${img.url}" target="_blank" class="news-carousel-item">
                        <div class="nc-thumb">
                            <span class="nc-source-badge">${domain}</span>
                            <img src="${img.image}" alt="" loading="lazy">
                        </div>
                        <div class="nc-content">
                            <div class="nc-title">${img.title}</div>
                            <div class="nc-meta">Suggested Match • Just now</div>
                        </div>
                    </a>
                `;
            });
            imageCarousel.innerHTML = imgHTML;
            imageCarousel.style.display = 'flex';
        }

        // 3.8 Render Knowledge Panel (Only on 'All' tab)
        if (currentSearchType === 'all' && data.knowledge_panel) {
            const kp = data.knowledge_panel;
            let imgHtml = '';
            if (kp.thumbnail_url) {
                imgHtml = `<div class="kp-image-container"><img src="${kp.thumbnail_url}" alt="${kp.title}"></div>`;
            }

            let quickFactsHtml = '';
            if (kp.quick_facts) {
                let rows = '';
                for (const [key, value] of Object.entries(kp.quick_facts)) {
                    rows += `
                        <div class="kp-fact-row">
                            <span class="kp-fact-key">${key}</span>
                            <span class="kp-fact-val">${value}</span>
                        </div>
                    `;
                }
                quickFactsHtml = `<div class="kp-facts-grid">${rows}</div>`;
            }

            knowledgePanel.innerHTML = `
                ${imgHtml}
                <div class="kp-content">
                    <h2 class="kp-title">${kp.title}</h2>
                    <div class="kp-subtitle">
                        <i class="ph-fill ph-check-circle" style="color: var(--accent-brand);"></i> Verified source
                    </div>
                    <div class="kp-extract">${kp.extract}</div>
                    ${quickFactsHtml}
                    <a href="${kp.url}" target="_blank" class="kp-link">
                        <i class="ph ph-wikipedia-logo"></i> Read more on Wikipedia
                    </a>
                </div>
            `;
            knowledgePanel.style.display = 'block';
        }

        // 4. Render HTML Cards
        let htmlStr = '';

        if (currentSearchType === 'images') {
            htmlStr += '<div class="image-grid-results">';
            data.results.forEach((result, idx) => {
                const delay = (idx * 0.04).toFixed(2);
                const safeTitle = encodeURIComponent(result.title || '');
                const safeSnippet = encodeURIComponent(result.snippet || '');

                let domain = "example.com";
                try {
                    domain = new URL(result.url).hostname;
                } catch (e) { }

                // In DDG image search, the snippet is actually the "source" name.
                let sourceName = result.snippet || domain;

                htmlStr += `
                    <div class="image-grid-item fade-in-up" style="cursor: pointer; animation-delay: ${delay}s"
                         data-type="image"
                         data-media="${result.thumbnail_url || result.url}"
                         data-url="${result.url}"
                         data-title="${safeTitle}"
                         data-source="${safeSnippet}">
                        <div class="img-wrapper">
                            <img src="${result.thumbnail_url || result.url}" alt="${result.title}" loading="lazy">
                        </div>
                        <div class="img-meta">
                            <div class="img-source-wrap">
                                <img class="img-source-icon" src="https://www.google.com/s2/favicons?domain=${domain}&sz=32" alt="" loading="lazy">
                                <span class="img-source-text">${sourceName}</span>
                            </div>
                            <div class="img-title">${result.title}</div>
                        </div>
                    </div>
                `;
            });
            htmlStr += '</div>';
        } else if (currentSearchType === 'videos') {
            htmlStr += '<div class="video-grid-results">';
            data.results.forEach((result, idx) => {
                const delay = (idx * 0.04).toFixed(2);
                const safeTitle = encodeURIComponent(result.title || '');
                const safeSnippet = encodeURIComponent(result.snippet || '');
                htmlStr += `
                    <div class="video-grid-item fade-in-up" style="cursor: pointer; animation-delay: ${delay}s"
                         data-type="video"
                         data-media="${result.url}"
                         data-url="${result.url}"
                         data-title="${safeTitle}"
                         data-source="${safeSnippet}">
                        <div class="video-thumb-wrapper">
                            ${result.thumbnail_url ? `<img src="${result.thumbnail_url}" alt="${result.title}" loading="lazy">` : `<div class="video-placeholder"></div>`}
                            <div class="play-overlay"><i class="ph-fill ph-play-circle"></i></div>
                        </div>
                        <div class="video-meta">
                            <div class="video-title">${result.title}</div>
                            <div class="video-source">${result.snippet}</div>
                        </div>
                    </div>
                `;
            });
            htmlStr += '</div>';
        } else if (currentSearchType === 'news') {
            htmlStr += '<div class="news-list-results">';
            data.results.forEach((result, idx) => {
                const delay = (idx * 0.04).toFixed(2);
                htmlStr += `
                    <a href="${result.url}" target="_blank" class="news-list-item fade-in-up" style="animation-delay: ${delay}s">
                        <div class="news-content-block">
                            <div class="news-source-meta">${result.snippet}</div>
                            <div class="news-title">${result.title}</div>
                        </div>
                        ${result.thumbnail_url ? `
                        <div class="news-thumb-block">
                            <img src="${result.thumbnail_url}" alt="" loading="lazy">
                        </div>` : ''}
                    </a>
                `;
            });
            htmlStr += '</div>';
        } else {
            data.results.forEach((result, idx) => {
                // Safe URL parsing for domain
                let domain = "example.com";
                let path = "";
                try {
                    const u = new URL(result.url);
                    domain = u.hostname;
                    path = u.pathname;
                    if (path.length > 20) path = path.substring(0, 20) + "...";
                } catch (e) { }

                // Add standard animation delay
                const delay = (idx * 0.04).toFixed(2);

                // Normalize snippet length
                let description = result.snippet;
                if (description && description.length > 200) {
                    description = description.substring(0, 197) + "...";
                }

                htmlStr += `
                    <div class="result-card fade-in-up" style="animation-delay: ${delay}s">
                        <div class="result-content-container">
                            <div class="result-text-block">
                                <div style="display: flex; flex-direction: column; gap: 4px;">
                                    <a href="${result.url}" target="_blank" class="result-url-group">
                                        <img src="https://www.google.com/s2/favicons?domain=${domain}" alt="" />
                                        <span>
                                            <span class="url-text">${domain}</span><span class="url-path">${path}</span>
                                        </span>
                                    </a>
                                    <a href="${result.url}" target="_blank" class="result-title">${result.title}</a>
                                </div>
                                <div class="result-snippet">${description}</div>
                            </div>
                            ${result.thumbnail_url ? `
                            <div class="result-thumb-container">
                                <img src="${result.thumbnail_url}" alt="" loading="lazy">
                            </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
        }
        resultsList.innerHTML = htmlStr;

        // Bind Media Modal Events
        document.querySelectorAll('.image-grid-item, .video-grid-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const type = item.dataset.type;
                const mediaUrl = item.dataset.media;
                const sourceUrl = item.dataset.url;
                const title = decodeURIComponent(item.dataset.title);
                const source = decodeURIComponent(item.dataset.source);
                openMediaModal(type, mediaUrl, sourceUrl, title, source);
            });
        });

        // 5. Build Pagination
        if (data.total_pages > 1) {
            buildPagination(data.page, data.total_pages);
            pagination.style.display = 'flex';
        }
    }

    function buildPagination(currPage, totalPages) {
        prevBtn.disabled = currPage === 1;
        nextBtn.disabled = currPage === totalPages;

        let pgHtml = '';

        // Always show up to 5 surrounding pages to prevent UI stretching
        let startPage = Math.max(1, currPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);

        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }

        for (let i = startPage; i <= endPage; i++) {
            if (i === currPage) {
                pgHtml += `<div class="pg-num active">${i}</div>`;
            } else {
                pgHtml += `<div class="pg-num" onclick="window.goToPage(${i})">${i}</div>`;
            }
        }
        pageNumbers.innerHTML = pgHtml;
    }

    async function streamAiSummary(query, context) {
        try {
            const response = await fetch(`${API_BASE}/stream_ai`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, context })
            });

            if (!response.ok) throw new Error("Stream failed");

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let fullText = "";
            aiSummaryText.innerHTML = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        if (dataStr === '[DONE]') break;
                        try {
                            const dataObj = JSON.parse(dataStr);
                            if (dataObj.error) {
                                fullText = dataObj.error;
                            } else if (dataObj.text) {
                                fullText += dataObj.text;
                            }
                            aiSummaryText.innerHTML = marked.parse(fullText);
                        } catch (e) { }
                    }
                }
            }

            // Post-stream cleanup
            if (fullText.length > 350) {
                aiShowMore.style.display = 'inline-flex';
            }

            aiHistoryStr = fullText;

        } catch (error) {
            aiSummaryText.innerHTML = `<span style="color: var(--text-muted)">Failed to generate AI summary.</span>`;
        }
    }

    async function streamChatFollowUp(query, context, history, bubbleElement) {
        try {
            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, context, history })
            });

            if (!response.ok) throw new Error("Stream failed");

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let fullText = "";
            bubbleElement.innerHTML = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        if (dataStr === '[DONE]') break;
                        try {
                            const dataObj = JSON.parse(dataStr);
                            if (dataObj.error) {
                                fullText = dataObj.error;
                            } else if (dataObj.text) {
                                fullText += dataObj.text;
                                // Automatically scroll the thread to the bottom
                                aiChatThread.scrollTop = aiChatThread.scrollHeight;
                            }
                            bubbleElement.innerHTML = marked.parse(fullText);
                        } catch (e) { }
                    }
                }
            }

            aiHistoryStr += `\n\nUser: ${query}\nAI: ${fullText}`;
        } catch (error) {
            bubbleElement.innerHTML = `<span style="color: var(--text-muted)">Failed to generate AI response.</span>`;
        } finally {
            aiChatInput.disabled = false;
            aiChatInput.focus();
        }
    }

    // Global helper for the inline onclick handlers in pagination
    window.goToPage = function (p) {
        executeSearch(currentQuery, p);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // --- Media Modal Logic ---
    const mediaModal = document.getElementById('media-modal');
    const mediaModalClose = document.getElementById('media-modal-close');
    const mediaModalBackdrop = document.getElementById('media-modal-backdrop');
    const mediaModalBody = document.getElementById('media-modal-body');
    const mediaModalTitle = document.getElementById('media-modal-title');
    const mediaModalSource = document.getElementById('media-modal-source');
    const mediaModalLink = document.getElementById('media-modal-link');
    const mediaModalMeta = document.getElementById('media-modal-meta');

    function getYoutubeEmbedUrl(url) {
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
        const match = url.match(regExp);
        if (match && match[2].length === 11) {
            return 'https://www.youtube.com/embed/' + match[2] + '?autoplay=1';
        }
        return null;
    }

    window.openMediaModal = function (type, mediaUrl, sourceUrl, title, source) {
        mediaModalBody.innerHTML = '';
        mediaModalTitle.textContent = title;
        mediaModalSource.textContent = source;
        mediaModalLink.href = sourceUrl;
        mediaModalMeta.style.display = 'flex';

        if (type === 'image') {
            mediaModalBody.innerHTML = `<img src="${mediaUrl}" alt="Full screen image">`;
        } else if (type === 'video') {
            const embedUrl = getYoutubeEmbedUrl(sourceUrl) || getYoutubeEmbedUrl(mediaUrl);
            if (embedUrl) {
                mediaModalBody.innerHTML = `<iframe src="${embedUrl}" allow="autoplay; encrypted-media" allowfullscreen></iframe>`;
            } else {
                // Fallback if we cannot embed natively
                mediaModalBody.innerHTML = `
                    <div style="text-align: center; color: white;">
                        <i class="ph-duotone ph-video-camera-slash" style="font-size: 4rem; margin-bottom: 16px;"></i>
                        <p style="font-size: 1.2rem; margin-bottom: 8px;">Video embedding not supported.</p>
                        <p style="color: #aaa;">Click "Visit Site" below to watch on the original platform.</p>
                    </div>`;
            }
        }

        mediaModal.classList.add('active');
        document.body.style.overflow = 'hidden'; // block background scroll
    };

    function closeMediaModal() {
        mediaModal.classList.remove('active');
        document.body.style.overflow = '';
        setTimeout(() => {
            mediaModalBody.innerHTML = '';
        }, 300);
    }

    if (mediaModalClose) mediaModalClose.addEventListener('click', closeMediaModal);
    if (mediaModalBackdrop) mediaModalBackdrop.addEventListener('click', closeMediaModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && mediaModal && mediaModal.classList.contains('active')) {
            closeMediaModal();
        }
    });

});
