import React, { useState, useEffect } from 'react';
import { Database, GlobeHemisphereWest } from '@phosphor-icons/react';
import { useSearchAPI } from './hooks/useSearchAPI';

import Header from './components/layout/Header';
import SearchTabs from './components/layout/SearchTabs';
import Pagination from './components/layout/Pagination';

import ResultCard from './components/results/ResultCard';
import { ImageGridItem, VideoGridItem, NewsListItem, NewsCarouselItem } from './components/results/MediaItems';

import AiOverview from './components/widgets/AiOverview';
import KnowledgePanel from './components/widgets/KnowledgePanel';
import InstantWidgets from './components/widgets/InstantWidgets';
import MediaModal from './components/shared/MediaModal';

import './index.css'; // Responsive Google-Style UI

function App() {
  const api = useSearchAPI();
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [hasSearched, setHasSearched] = useState(false);

  // Modal State
  const [modalData, setModalData] = useState({ isOpen: false });

  useEffect(() => {
    // Initial warmup
    api.fetchStats();
  }, []);

  // Debounce autocomplete
  useEffect(() => {
    const handler = setTimeout(() => {
      if (query.length >= 2 && !hasSearched) {
        api.fetchSuggestions(query);
      } else {
        api.setSuggestions([]);
      }
    }, 200);
    return () => clearTimeout(handler);
  }, [query, hasSearched]);

  const handleSearch = async (submitQuery, page = 1) => {
    setHasSearched(true);
    setActiveTab('all');
    api.performSearch(submitQuery, page, 'all');
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    api.performSearch(query, 1, tabId);
  };

  const handlePageChange = (newPage) => {
    api.performSearch(query, newPage, activeTab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const openMediaModal = (hit, type) => {
    // Determine source
    let source = hit.image || hit.thumbnail_url;
    if (type === 'video') {
      // Rough youtube embed translation
      source = hit.url.replace('watch?v=', 'embed/');
    }
    setModalData({
      isOpen: true,
      mediaType: type,
      mediaSource: source,
      metaTitle: hit.title.replace(/<\/?[^>]+(>|$)/g, ""), // strip bold tags
      metaUrl: hit.url
    });
  };

  // Zero State View
  if (!hasSearched) {
    return (
      <div className="app-layout state-home">
        <Header
          query={query} setQuery={setQuery}
          onSearch={handleSearch}
          hasSearched={hasSearched}
          suggestions={api.suggestions}
          setSuggestions={api.setSuggestions}
        />
        <div className="zero-state" style={{ display: 'flex' }}>
          <div className="stats-badge">
            <Database size={16} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
            {api.stats ? `${api.stats.indexed_pages} pages indexed` : 'Warming up index...'}
          </div>
          <GlobeHemisphereWest weight="duotone" size={200} color="#e8eaed" style={{ marginTop: '40px' }} />
        </div>
      </div>
    );
  }

  // Searched View
  return (
    <div className={`app-layout state-searched ${activeTab !== 'all' ? 'state-full-width' : ''}`}>
      <Header
        query={query} setQuery={setQuery}
        onSearch={handleSearch}
        hasSearched={hasSearched}
        goHome={() => setHasSearched(false) || setQuery('')}
        suggestions={api.suggestions}
        setSuggestions={api.setSuggestions}
      />
      <SearchTabs activeTab={activeTab} onTabChange={handleTabChange} />

      <main className="content-area">
        {api.searchMeta.total_hits > 0 && activeTab === 'all' && (
          <div className="results-meta" style={{ display: 'block' }}>
            Found {api.searchMeta.total_hits} results in {api.searchMeta.total_time_ms}ms
          </div>
        )}

        {api.spellCorrection && (
          <div className="spell-correction" style={{ display: 'flex' }}>
            Did you mean: <a href="#" onClick={(e) => { e.preventDefault(); setQuery(api.spellCorrection); handleSearch(api.spellCorrection); }}>{api.spellCorrection}</a>
          </div>
        )}

        {api.isLoading && (
          <div className="loader-wrap" style={{ display: 'flex' }}>
            <div className="nexus-spinner"></div>
          </div>
        )}

        {!api.isLoading && (
          <div className="main-grid">
            <div className="results-layout">

              {/* Conditional Layouts based on Tab */}
              {activeTab === 'all' && (
                <>
                  <InstantWidgets widget={api.instantWidget} />
                  <AiOverview query={query} results={api.results} />

                  {api.images.length > 0 && (
                    <div className="image-carousel">
                      {api.images.map(hit => (
                        <NewsCarouselItem key={hit.id} hit={hit} onClick={(h) => openMediaModal(h, 'image')} />
                      ))}
                    </div>
                  )}

                  {api.results.map(hit => <ResultCard key={hit.id} hit={hit} />)}
                </>
              )}

              {activeTab === 'images' && (
                <div className="image-grid-results">
                  {api.results.map(hit => <ImageGridItem key={hit.id} hit={hit} onClick={(h) => openMediaModal(h, 'image')} />)}
                </div>
              )}

              {activeTab === 'videos' && (
                <div className="video-grid-results">
                  {api.results.map(hit => <VideoGridItem key={hit.id} hit={hit} onClick={(h) => openMediaModal(h, 'video')} />)}
                </div>
              )}

              {activeTab === 'news' && (
                <div className="news-list-results">
                  {api.results.map(hit => <NewsListItem key={hit.id} hit={hit} />)}
                </div>
              )}
            </div>

            {/* Knowledge Panel only on 'all' tab */}
            {activeTab === 'all' && api.knowledgePanel && (
              <div>
                <KnowledgePanel kp={api.knowledgePanel} />
              </div>
            )}
          </div>
        )}

        {!api.isLoading && <Pagination page={api.searchMeta.page} totalPages={api.searchMeta.total_pages} onPageChange={handlePageChange} />}
      </main>

      <MediaModal
        isOpen={modalData.isOpen}
        onClose={() => setModalData({ isOpen: false })}
        {...modalData}
      />
    </div>
  );
}

export default App;
