import { useState, useCallback } from 'react';
import axios from 'axios';

export function useSearchAPI() {
    const [results, setResults] = useState([]);
    const [images, setImages] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [stats, setStats] = useState(null);
    const [aiSummary, setAiSummary] = useState(null);
    const [spellCorrection, setSpellCorrection] = useState('');
    const [instantWidget, setInstantWidget] = useState(null);
    const [knowledgePanel, setKnowledgePanel] = useState(null);

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searchMeta, setSearchMeta] = useState({ page: 1, total_pages: 1, total_hits: 0, total_time_ms: 0 });

    const fetchStats = useCallback(async () => {
        try {
            const res = await axios.get('/api/stats');
            setStats(res.data);
        } catch (e) {
            console.error(e);
        }
    }, []);

    const fetchSuggestions = useCallback(async (query) => {
        if (!query || query.length < 2) {
            setSuggestions([]);
            return;
        }
        try {
            const res = await axios.get(`/api/suggest?q=${encodeURIComponent(query)}`);
            setSuggestions(res.data);
        } catch (e) {
            console.error(e);
        }
    }, []);

    const performSearch = useCallback(async (query, page = 1, type = 'all') => {
        if (!query.trim()) return;

        setIsLoading(true);
        setError(null);
        setResults([]);
        setInstantWidget(null);
        setKnowledgePanel(null); // Clear knowledge panel on new search
        if (page === 1) setAiSummary(null);

        try {
            const res = await axios.get(`/api/search?q=${encodeURIComponent(query)}&page=${page}&type=${type}`);
            const data = res.data;

            setResults(data.results || []);
            setSearchMeta({
                page: data.page,
                total_pages: data.total_pages,
                total_hits: data.total_hits,
                total_time_ms: data.total_time_ms
            });

            setSpellCorrection(data.spell_correction || '');
            setInstantWidget(data.instant_widget || null);
            setKnowledgePanel(data.knowledge_panel || null);

            // Separate image carousel for "all" tab
            if (type === 'all' && data.image_results) {
                setImages(data.image_results);
            } else if (type !== 'all') {
                setImages([]);
            }

        } catch (e) {
            console.error(e);
            setError('An error occurred while fetching results.');
        } finally {
            setIsLoading(false);
        }
    }, []);

    return {
        results,
        images,
        suggestions,
        stats,
        aiSummary,
        spellCorrection,
        instantWidget,
        knowledgePanel,
        isLoading,
        error,
        searchMeta,
        fetchStats,
        fetchSuggestions,
        performSearch,
        setSuggestions,
        setAiSummary // For streaming updates later
    };
}
