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
        searchInput.value = '';
        clearBtn.style.display = 'none';
        resultsList.innerHTML = '';
        resultsMeta.style.display = 'none';
        spellCorrection.style.display = 'none';
        pagination.style.display = 'none';
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
        resultsMeta.style.display = 'none';
        spellCorrection.style.display = 'none';
        pagination.style.display = 'none';
        loader.style.display = 'flex';

        try {
            const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&page=${page}`);
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

        // 4. Render HTML Cards
        let htmlStr = '';
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

            htmlStr += `
                <div class="result-card" style="animation-delay: ${delay}s">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <a href="${result.url}" target="_blank" class="result-url-group">
                            <img src="https://www.google.com/s2/favicons?domain=${domain}" alt="" />
                            <span>
                                <span class="url-text">${domain}</span><span class="url-path">${path}</span>
                            </span>
                        </a>
                        <a href="${result.url}" target="_blank" class="result-title">${result.title}</a>
                    </div>
                    <div class="result-snippet">${result.snippet}</div>
                </div>
            `;
        });
        resultsList.innerHTML = htmlStr;

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

    // Global helper for the inline onclick handlers in pagination
    window.goToPage = function (p) {
        executeSearch(currentQuery, p);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

});
