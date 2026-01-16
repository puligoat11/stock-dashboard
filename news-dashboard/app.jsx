const { useState, useEffect, useCallback, useMemo, useRef } = React;

// ============================================
// API CONFIGURATION & SERVICES
// ============================================

const API_KEYS_STORAGE_KEY = 'pulse-api-keys';

const getApiKeys = () => {
    try {
        return JSON.parse(localStorage.getItem(API_KEYS_STORAGE_KEY)) || {};
    } catch {
        return {};
    }
};

const saveApiKeys = (keys) => {
    localStorage.setItem(API_KEYS_STORAGE_KEY, JSON.stringify(keys));
};

// Finnhub API for stocks and market news
const FinnhubAPI = {
    baseUrl: 'https://finnhub.io/api/v1',

    async getQuote(symbol, apiKey) {
        const res = await fetch(`${this.baseUrl}/quote?symbol=${symbol}&token=${apiKey}`);
        if (!res.ok) throw new Error('Failed to fetch quote');
        return res.json();
    },

    async getCompanyProfile(symbol, apiKey) {
        const res = await fetch(`${this.baseUrl}/stock/profile2?symbol=${symbol}&token=${apiKey}`);
        if (!res.ok) throw new Error('Failed to fetch profile');
        return res.json();
    },

    async getMarketNews(apiKey, category = 'general') {
        const res = await fetch(`${this.baseUrl}/news?category=${category}&token=${apiKey}`);
        if (!res.ok) throw new Error('Failed to fetch news');
        return res.json();
    },

    async getCompanyNews(symbol, apiKey) {
        const today = new Date();
        const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
        const from = weekAgo.toISOString().split('T')[0];
        const to = today.toISOString().split('T')[0];
        const res = await fetch(`${this.baseUrl}/company-news?symbol=${symbol}&from=${from}&to=${to}&token=${apiKey}`);
        if (!res.ok) throw new Error('Failed to fetch company news');
        return res.json();
    },

    async searchSymbols(query, apiKey) {
        const res = await fetch(`${this.baseUrl}/search?q=${query}&token=${apiKey}`);
        if (!res.ok) throw new Error('Failed to search');
        return res.json();
    },

    // WebSocket for real-time prices
    createSocket(apiKey, onMessage) {
        const socket = new WebSocket(`wss://ws.finnhub.io?token=${apiKey}`);
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'trade') {
                onMessage(data.data);
            }
        };
        return socket;
    }
};

// TheSportsDB API for sports data
const SportsAPI = {
    baseUrl: 'https://www.thesportsdb.com/api/v1/json',

    async searchTeams(query, apiKey = '3') {
        const res = await fetch(`${this.baseUrl}/${apiKey}/searchteams.php?t=${encodeURIComponent(query)}`);
        if (!res.ok) throw new Error('Failed to search teams');
        return res.json();
    },

    async getTeamDetails(teamId, apiKey = '3') {
        const res = await fetch(`${this.baseUrl}/${apiKey}/lookupteam.php?id=${teamId}`);
        if (!res.ok) throw new Error('Failed to get team');
        return res.json();
    },

    async getLastEvents(teamId, apiKey = '3') {
        const res = await fetch(`${this.baseUrl}/${apiKey}/eventslast.php?id=${teamId}`);
        if (!res.ok) throw new Error('Failed to get events');
        return res.json();
    },

    async getNextEvents(teamId, apiKey = '3') {
        const res = await fetch(`${this.baseUrl}/${apiKey}/eventsnext.php?id=${teamId}`);
        if (!res.ok) throw new Error('Failed to get events');
        return res.json();
    },

    async getLeagues(apiKey = '3') {
        const res = await fetch(`${this.baseUrl}/${apiKey}/all_leagues.php`);
        if (!res.ok) throw new Error('Failed to get leagues');
        return res.json();
    },

    async getTeamsByLeague(leagueId, apiKey = '3') {
        const res = await fetch(`${this.baseUrl}/${apiKey}/lookup_all_teams.php?id=${leagueId}`);
        if (!res.ok) throw new Error('Failed to get teams');
        return res.json();
    }
};

// News API for financial news (works on localhost)
const NewsAPI = {
    baseUrl: 'https://newsapi.org/v2',

    async getTopHeadlines(apiKey, category = 'business', country = 'us') {
        const res = await fetch(`${this.baseUrl}/top-headlines?category=${category}&country=${country}&apiKey=${apiKey}`);
        if (!res.ok) throw new Error('Failed to fetch news');
        return res.json();
    },

    async searchNews(apiKey, query) {
        const res = await fetch(`${this.baseUrl}/everything?q=${encodeURIComponent(query)}&sortBy=publishedAt&language=en&apiKey=${apiKey}`);
        if (!res.ok) throw new Error('Failed to search news');
        return res.json();
    }
};

// Pre-configured teams data with TheSportsDB IDs
const TEAMS_DATA = {
    nba: [
        { id: '134880', name: 'Miami Heat', abbr: 'MIA', league: 'NBA', color: '#98002E' },
        { id: '134867', name: 'Los Angeles Lakers', abbr: 'LAL', league: 'NBA', color: '#552583' },
        { id: '134860', name: 'Boston Celtics', abbr: 'BOS', league: 'NBA', color: '#007A33' },
        { id: '134865', name: 'Golden State Warriors', abbr: 'GSW', league: 'NBA', color: '#1D428A' },
        { id: '134862', name: 'Chicago Bulls', abbr: 'CHI', league: 'NBA', color: '#CE1141' },
        { id: '134861', name: 'Brooklyn Nets', abbr: 'BKN', league: 'NBA', color: '#000000' },
        { id: '134882', name: 'New York Knicks', abbr: 'NYK', league: 'NBA', color: '#006BB6' },
        { id: '134884', name: 'Philadelphia 76ers', abbr: 'PHI', league: 'NBA', color: '#006BB6' },
    ],
    nfl: [
        { id: '134920', name: 'New England Patriots', abbr: 'NE', league: 'NFL', color: '#002244' },
        { id: '134918', name: 'Kansas City Chiefs', abbr: 'KC', league: 'NFL', color: '#E31837' },
        { id: '134948', name: 'San Francisco 49ers', abbr: 'SF', league: 'NFL', color: '#AA0000' },
        { id: '134934', name: 'Dallas Cowboys', abbr: 'DAL', league: 'NFL', color: '#003594' },
        { id: '134916', name: 'Green Bay Packers', abbr: 'GB', league: 'NFL', color: '#203731' },
        { id: '134922', name: 'Buffalo Bills', abbr: 'BUF', league: 'NFL', color: '#00338D' },
        { id: '134924', name: 'Miami Dolphins', abbr: 'MIA', league: 'NFL', color: '#008E97' },
        { id: '134942', name: 'Las Vegas Raiders', abbr: 'LV', league: 'NFL', color: '#000000' },
    ],
    soccer: [
        { id: '133604', name: 'AC Milan', abbr: 'ACM', league: 'Serie A', color: '#FB090B' },
        { id: '133738', name: 'Real Madrid', abbr: 'RMA', league: 'La Liga', color: '#FEBE10' },
        { id: '133613', name: 'Manchester City', abbr: 'MCI', league: 'Premier League', color: '#6CABDD' },
        { id: '133739', name: 'FC Barcelona', abbr: 'FCB', league: 'La Liga', color: '#A50044' },
        { id: '133714', name: 'Paris Saint-Germain', abbr: 'PSG', league: 'Ligue 1', color: '#004170' },
        { id: '133612', name: 'Manchester United', abbr: 'MUN', league: 'Premier League', color: '#DA291C' },
        { id: '133610', name: 'Arsenal', abbr: 'ARS', league: 'Premier League', color: '#EF0107' },
        { id: '133616', name: 'Liverpool', abbr: 'LIV', league: 'Premier League', color: '#C8102E' },
    ],
};

// Default stocks for watchlist
const DEFAULT_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'SPY'];

// ============================================
// UTILITY HOOKS
// ============================================

const useLocalStorage = (key, initialValue) => {
    const [storedValue, setStoredValue] = useState(() => {
        try {
            const item = window.localStorage.getItem(key);
            return item ? JSON.parse(item) : initialValue;
        } catch (error) {
            return initialValue;
        }
    });

    const setValue = (value) => {
        try {
            const valueToStore = value instanceof Function ? value(storedValue) : value;
            setStoredValue(valueToStore);
            window.localStorage.setItem(key, JSON.stringify(valueToStore));
        } catch (error) {
            console.error(error);
        }
    };

    return [storedValue, setValue];
};

const useInterval = (callback, delay) => {
    const savedCallback = useRef();

    useEffect(() => {
        savedCallback.current = callback;
    }, [callback]);

    useEffect(() => {
        if (delay !== null) {
            const id = setInterval(() => savedCallback.current(), delay);
            return () => clearInterval(id);
        }
    }, [delay]);
};

// ============================================
// ICONS
// ============================================

const Icons = {
    Sports: () => (
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            <path d="M2 12h20"/>
        </svg>
    ),
    Finance: () => (
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
    ),
    Stocks: () => (
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
            <polyline points="16 7 22 7 22 13"/>
        </svg>
    ),
    Back: () => (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
    ),
    Check: () => (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"/>
        </svg>
    ),
    Search: () => (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
    ),
    Clock: () => (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
        </svg>
    ),
    Live: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="6"/>
        </svg>
    ),
    TrendUp: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
            <polyline points="17 6 23 6 23 12"/>
        </svg>
    ),
    TrendDown: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/>
            <polyline points="17 18 23 18 23 12"/>
        </svg>
    ),
    Star: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="1">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
        </svg>
    ),
    StarOutline: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
        </svg>
    ),
    Refresh: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"/>
        </svg>
    ),
    Settings: () => (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
        </svg>
    ),
    ExternalLink: () => (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/>
        </svg>
    ),
    Alert: () => (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
    ),
    Key: () => (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
        </svg>
    ),
};

// ============================================
// STYLES
// ============================================

const styles = `
    .app {
        min-height: 100vh;
        min-height: 100dvh;
        padding-bottom: env(safe-area-inset-bottom, 20px);
    }

    /* Header */
    .header {
        position: sticky;
        top: 0;
        z-index: 100;
        padding: 16px 20px;
        background: linear-gradient(to bottom, var(--bg-primary) 0%, var(--bg-primary) 70%, transparent 100%);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }

    .header-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        max-width: 600px;
        margin: 0 auto;
    }

    .header-back {
        display: flex;
        align-items: center;
        gap: 8px;
        background: none;
        border: none;
        color: var(--text-secondary);
        font-family: inherit;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        padding: 8px 12px;
        margin: -8px -12px;
        border-radius: var(--radius-md);
        transition: all var(--transition-fast);
    }

    .header-back:hover {
        color: var(--text-primary);
        background: var(--bg-elevated);
    }

    .header-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .header-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: var(--text-muted);
    }

    .header-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        color: var(--text-secondary);
        cursor: pointer;
        transition: all var(--transition-fast);
    }

    .header-btn:hover {
        background: var(--bg-elevated);
        color: var(--text-primary);
    }

    /* Home Screen */
    .home {
        padding: 20px;
        max-width: 600px;
        margin: 0 auto;
    }

    .home-hero {
        text-align: center;
        padding: 40px 0 50px;
    }

    .home-logo {
        font-family: 'Outfit', sans-serif;
        font-size: 48px;
        font-weight: 700;
        letter-spacing: -2px;
        background: linear-gradient(135deg, var(--sports-primary), var(--finance-primary), var(--stocks-primary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
    }

    .home-tagline {
        font-size: 15px;
        color: var(--text-secondary);
        font-weight: 400;
    }

    .home-cards {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .category-card {
        position: relative;
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 28px 24px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-xl);
        cursor: pointer;
        transition: all var(--transition-medium);
        overflow: hidden;
        text-decoration: none;
        color: inherit;
    }

    .category-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        opacity: 0;
        transition: opacity var(--transition-medium);
    }

    .category-card.sports::before {
        background: linear-gradient(135deg, var(--sports-glow) 0%, transparent 60%);
    }

    .category-card.finance::before {
        background: linear-gradient(135deg, var(--finance-glow) 0%, transparent 60%);
    }

    .category-card.stocks::before {
        background: linear-gradient(135deg, var(--stocks-glow) 0%, transparent 60%);
    }

    .category-card:hover::before,
    .category-card:active::before {
        opacity: 1;
    }

    .category-card:hover {
        transform: translateY(-2px);
        border-color: var(--border-medium);
        box-shadow: var(--shadow-card);
    }

    .category-card:active {
        transform: translateY(0) scale(0.99);
    }

    .category-icon {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        border-radius: var(--radius-lg);
        flex-shrink: 0;
    }

    .category-card.sports .category-icon {
        background: linear-gradient(135deg, var(--sports-primary), var(--sports-secondary));
        box-shadow: 0 4px 20px var(--sports-glow);
    }

    .category-card.finance .category-icon {
        background: linear-gradient(135deg, var(--finance-primary), var(--finance-secondary));
        box-shadow: 0 4px 20px var(--finance-glow);
    }

    .category-card.stocks .category-icon {
        background: linear-gradient(135deg, var(--stocks-primary), var(--stocks-secondary));
        box-shadow: 0 4px 20px var(--stocks-glow);
    }

    .category-content {
        position: relative;
        z-index: 1;
        flex: 1;
    }

    .category-title {
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .category-desc {
        font-size: 14px;
        color: var(--text-secondary);
    }

    .category-arrow {
        position: relative;
        z-index: 1;
        color: var(--text-muted);
        transition: transform var(--transition-fast);
    }

    .category-card:hover .category-arrow {
        transform: translateX(4px);
    }

    /* API Setup Screen */
    .api-setup {
        padding: 20px;
        max-width: 500px;
        margin: 0 auto;
    }

    .api-setup-header {
        text-align: center;
        margin-bottom: 32px;
    }

    .api-setup-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        background: linear-gradient(135deg, var(--stocks-primary), var(--finance-primary));
        border-radius: var(--radius-lg);
        margin-bottom: 16px;
    }

    .api-setup-title {
        font-size: 24px;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .api-setup-subtitle {
        font-size: 14px;
        color: var(--text-secondary);
        line-height: 1.6;
    }

    .api-field {
        margin-bottom: 20px;
    }

    .api-field-label {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .api-field-name {
        font-size: 14px;
        font-weight: 500;
    }

    .api-field-link {
        font-size: 12px;
        color: var(--stocks-primary);
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    .api-field-link:hover {
        text-decoration: underline;
    }

    .api-input {
        width: 100%;
        padding: 14px 16px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        color: var(--text-primary);
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        outline: none;
        transition: all var(--transition-fast);
    }

    .api-input::placeholder {
        color: var(--text-muted);
    }

    .api-input:focus {
        border-color: var(--stocks-primary);
    }

    .api-field-hint {
        font-size: 12px;
        color: var(--text-muted);
        margin-top: 6px;
    }

    .api-submit {
        width: 100%;
        padding: 16px;
        background: linear-gradient(135deg, var(--stocks-primary), var(--finance-primary));
        border: none;
        border-radius: var(--radius-lg);
        color: var(--bg-primary);
        font-family: inherit;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all var(--transition-fast);
        margin-top: 24px;
    }

    .api-submit:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px var(--stocks-glow);
    }

    .api-submit:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none;
    }

    .api-skip {
        display: block;
        width: 100%;
        text-align: center;
        margin-top: 16px;
        color: var(--text-muted);
        font-size: 14px;
        cursor: pointer;
        background: none;
        border: none;
        font-family: inherit;
    }

    .api-skip:hover {
        color: var(--text-secondary);
    }

    /* Section Header */
    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        margin-bottom: 16px;
    }

    .section-title {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    .section-title.sports { color: var(--sports-primary); }
    .section-title.finance { color: var(--finance-primary); }
    .section-title.stocks { color: var(--stocks-primary); }

    /* Sports Section */
    .sports-content {
        padding: 0 20px 20px;
        max-width: 600px;
        margin: 0 auto;
    }

    .league-group {
        margin-bottom: 24px;
    }

    .league-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 0 4px;
        margin-bottom: 12px;
    }

    .teams-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 10px;
    }

    .team-chip {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 16px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all var(--transition-fast);
        position: relative;
        overflow: hidden;
    }

    .team-chip::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background: var(--team-color, var(--sports-primary));
        opacity: 0.5;
        transition: opacity var(--transition-fast);
    }

    .team-chip:hover {
        border-color: var(--border-medium);
        background: var(--bg-elevated);
    }

    .team-chip.selected {
        border-color: var(--sports-primary);
        background: rgba(255, 107, 74, 0.1);
    }

    .team-chip.selected::before {
        opacity: 1;
    }

    .team-abbr {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary);
    }

    .team-league {
        font-size: 10px;
        color: var(--text-muted);
    }

    .team-check {
        margin-left: auto;
        color: var(--sports-primary);
        opacity: 0;
        transform: scale(0.8);
        transition: all var(--transition-fast);
    }

    .team-chip.selected .team-check {
        opacity: 1;
        transform: scale(1);
    }

    .continue-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 18px 24px;
        margin-top: 24px;
        background: linear-gradient(135deg, var(--sports-primary), var(--sports-secondary));
        border: none;
        border-radius: var(--radius-lg);
        color: white;
        font-family: inherit;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all var(--transition-fast);
        box-shadow: 0 4px 20px var(--sports-glow);
    }

    .continue-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        box-shadow: none;
    }

    .continue-btn:not(:disabled):hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 30px var(--sports-glow);
    }

    .continue-btn:not(:disabled):active {
        transform: translateY(0);
    }

    /* Dashboard styles */
    .dashboard {
        padding: 0 16px 20px;
        max-width: 600px;
        margin: 0 auto;
    }

    .team-tabs {
        display: flex;
        gap: 8px;
        padding: 0 4px 16px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }

    .team-tabs::-webkit-scrollbar {
        display: none;
    }

    .team-tab {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 16px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        color: var(--text-secondary);
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: all var(--transition-fast);
        white-space: nowrap;
        flex-shrink: 0;
    }

    .team-tab:hover {
        border-color: var(--border-medium);
    }

    .team-tab.active {
        background: var(--sports-primary);
        border-color: var(--sports-primary);
        color: white;
    }

    .dashboard-section {
        margin-bottom: 24px;
    }

    .dashboard-section-title {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 12px;
        padding: 0 4px;
    }

    /* Games / Schedule */
    .games-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .game-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        transition: all var(--transition-fast);
    }

    .game-card.live {
        border-color: var(--sports-primary);
        background: rgba(255, 107, 74, 0.08);
    }

    .game-date {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: var(--text-muted);
        width: 80px;
        flex-shrink: 0;
    }

    .game-info {
        flex: 1;
        min-width: 0;
    }

    .game-teams {
        font-size: 14px;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .game-league {
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 2px;
    }

    .game-result {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: var(--radius-sm);
        text-align: center;
    }

    .game-result.win {
        background: rgba(0, 212, 170, 0.15);
        color: var(--positive);
    }

    .game-result.loss {
        background: rgba(255, 71, 87, 0.15);
        color: var(--negative);
    }

    .game-result.draw {
        background: rgba(136, 136, 160, 0.15);
        color: var(--text-secondary);
    }

    .game-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: var(--text-secondary);
        text-align: right;
    }

    .live-badge {
        display: flex;
        align-items: center;
        gap: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        color: var(--sports-primary);
        text-transform: uppercase;
        animation: pulse-live 2s infinite;
    }

    @keyframes pulse-live {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* News list */
    .news-list {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .news-item {
        padding: 14px 16px;
        background: var(--bg-card);
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all var(--transition-fast);
    }

    .news-item:first-child {
        border-radius: var(--radius-md) var(--radius-md) 4px 4px;
    }

    .news-item:last-child {
        border-radius: 4px 4px var(--radius-md) var(--radius-md);
    }

    .news-item:only-child {
        border-radius: var(--radius-md);
    }

    .news-item:hover {
        background: var(--bg-elevated);
    }

    .news-item a {
        color: inherit;
        text-decoration: none;
    }

    .news-headline {
        font-size: 14px;
        font-weight: 500;
        line-height: 1.4;
        margin-bottom: 6px;
    }

    .news-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: var(--text-muted);
    }

    .news-source {
        font-weight: 500;
        color: var(--text-secondary);
    }

    .news-breaking {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        background: rgba(255, 71, 87, 0.2);
        color: var(--negative);
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        border-radius: 4px;
        margin-right: 8px;
    }

    .news-image {
        width: 60px;
        height: 60px;
        border-radius: var(--radius-sm);
        object-fit: cover;
        flex-shrink: 0;
    }

    /* Finance Section */
    .finance-content {
        padding: 0 16px 20px;
        max-width: 600px;
        margin: 0 auto;
    }

    .filter-tabs {
        display: flex;
        gap: 8px;
        padding: 0 4px 20px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }

    .filter-tabs::-webkit-scrollbar {
        display: none;
    }

    .filter-tab {
        padding: 8px 16px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 100px;
        color: var(--text-secondary);
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all var(--transition-fast);
        white-space: nowrap;
        flex-shrink: 0;
    }

    .filter-tab:hover {
        border-color: var(--border-medium);
    }

    .filter-tab.active {
        background: var(--finance-primary);
        border-color: var(--finance-primary);
        color: var(--bg-primary);
    }

    .finance-news-item {
        display: flex;
        gap: 16px;
        padding: 18px 16px;
        background: var(--bg-card);
        border-radius: var(--radius-md);
        margin-bottom: 8px;
        cursor: pointer;
        transition: all var(--transition-fast);
        border: 1px solid var(--border-subtle);
    }

    .finance-news-item:hover {
        background: var(--bg-elevated);
        border-color: var(--border-medium);
    }

    .finance-news-item.breaking {
        border-left: 3px solid var(--finance-primary);
    }

    .finance-news-content {
        flex: 1;
        min-width: 0;
    }

    .finance-category-tag {
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--finance-primary);
        margin-bottom: 8px;
    }

    /* Stocks Section */
    .stocks-content {
        padding: 0 16px 20px;
        max-width: 600px;
        margin: 0 auto;
    }

    .search-bar {
        position: relative;
        margin-bottom: 20px;
    }

    .search-input {
        width: 100%;
        padding: 14px 16px 14px 48px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        color: var(--text-primary);
        font-family: inherit;
        font-size: 15px;
        outline: none;
        transition: all var(--transition-fast);
    }

    .search-input::placeholder {
        color: var(--text-muted);
    }

    .search-input:focus {
        border-color: var(--stocks-primary);
        background: var(--bg-elevated);
    }

    .search-icon {
        position: absolute;
        left: 16px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-muted);
        pointer-events: none;
    }

    .search-results {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--bg-elevated);
        border: 1px solid var(--border-medium);
        border-radius: var(--radius-md);
        margin-top: 4px;
        max-height: 300px;
        overflow-y: auto;
        z-index: 50;
    }

    .search-result-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        cursor: pointer;
        transition: background var(--transition-fast);
    }

    .search-result-item:hover {
        background: var(--bg-card);
    }

    .watchlist-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        padding: 0 4px;
    }

    .watchlist-title {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stocks-grid {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .stock-card {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all var(--transition-fast);
    }

    .stock-card:hover {
        background: var(--bg-elevated);
        border-color: var(--border-medium);
    }

    .stock-card.expanded {
        flex-direction: column;
        align-items: stretch;
        gap: 16px;
    }

    .stock-main {
        display: flex;
        align-items: center;
        gap: 16px;
        width: 100%;
    }

    .stock-info {
        flex: 1;
    }

    .stock-symbol {
        font-family: 'JetBrains Mono', monospace;
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
    }

    .stock-name {
        font-size: 12px;
        color: var(--text-muted);
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 150px;
    }

    .stock-price-info {
        text-align: right;
    }

    .stock-price {
        font-family: 'JetBrains Mono', monospace;
        font-size: 16px;
        font-weight: 600;
    }

    .stock-change {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        margin-top: 2px;
    }

    .stock-change.positive {
        color: var(--positive);
    }

    .stock-change.negative {
        color: var(--negative);
    }

    .stock-star {
        color: var(--text-muted);
        cursor: pointer;
        padding: 4px;
        margin: -4px;
        transition: all var(--transition-fast);
    }

    .stock-star:hover {
        color: var(--finance-primary);
    }

    .stock-star.active {
        color: var(--finance-primary);
    }

    .stock-news {
        padding-top: 12px;
        border-top: 1px solid var(--border-subtle);
    }

    .stock-news-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 8px 0;
        font-size: 13px;
        color: var(--text-secondary);
    }

    .stock-news-item:first-child {
        padding-top: 0;
    }

    .stock-news-item a {
        color: inherit;
        text-decoration: none;
    }

    .stock-news-item a:hover {
        color: var(--text-primary);
    }

    /* Loading States */
    .loading {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
    }

    .loading-spinner {
        width: 32px;
        height: 32px;
        border: 3px solid var(--border-subtle);
        border-top-color: var(--stocks-primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    /* Refresh indicator */
    .refresh-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 8px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: var(--text-muted);
    }

    .refresh-indicator.active svg {
        animation: spin 2s linear infinite;
    }

    /* Error state */
    .error-state {
        text-align: center;
        padding: 40px 20px;
        color: var(--text-muted);
    }

    .error-icon {
        color: var(--negative);
        margin-bottom: 12px;
    }

    .error-message {
        font-size: 14px;
        margin-bottom: 16px;
    }

    .error-retry {
        padding: 10px 20px;
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        color: var(--text-primary);
        font-family: inherit;
        font-size: 14px;
        cursor: pointer;
        transition: all var(--transition-fast);
    }

    .error-retry:hover {
        background: var(--bg-card);
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: var(--text-muted);
    }

    .empty-state-icon {
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
    }

    .empty-state-text {
        font-size: 15px;
    }

    /* Animations */
    .fade-in {
        animation: fadeIn 0.3s ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .slide-in {
        animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    .stagger-1 { animation-delay: 0.05s; opacity: 0; animation-fill-mode: forwards; }
    .stagger-2 { animation-delay: 0.1s; opacity: 0; animation-fill-mode: forwards; }
    .stagger-3 { animation-delay: 0.15s; opacity: 0; animation-fill-mode: forwards; }
    .stagger-4 { animation-delay: 0.2s; opacity: 0; animation-fill-mode: forwards; }
    .stagger-5 { animation-delay: 0.25s; opacity: 0; animation-fill-mode: forwards; }
    .stagger-6 { animation-delay: 0.3s; opacity: 0; animation-fill-mode: forwards; }

    /* Last updated */
    .last-updated {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: var(--text-muted);
        text-align: center;
        padding: 8px;
    }
`;

// ============================================
// COMPONENTS
// ============================================

const Header = ({ title, onBack, showTime = true, onSettings, showSettings = false }) => {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    return (
        <header className="header">
            <div className="header-content">
                {onBack ? (
                    <button className="header-back" onClick={onBack}>
                        <Icons.Back />
                        <span>Back</span>
                    </button>
                ) : (
                    <div className="header-title">Pulse</div>
                )}
                <div className="header-actions">
                    {showTime && (
                        <div className="header-time">
                            {time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                    )}
                    {showSettings && (
                        <button className="header-btn" onClick={onSettings} title="API Settings">
                            <Icons.Settings />
                        </button>
                    )}
                </div>
            </div>
        </header>
    );
};

const ApiSetup = ({ onComplete, initialKeys = {} }) => {
    const [keys, setKeys] = useState({
        finnhub: initialKeys.finnhub || '',
        newsapi: initialKeys.newsapi || '',
    });

    const handleSubmit = () => {
        saveApiKeys(keys);
        onComplete(keys);
    };

    const canSubmit = keys.finnhub.trim().length > 0;

    return (
        <div className="api-setup fade-in">
            <div className="api-setup-header">
                <div className="api-setup-icon">
                    <Icons.Key />
                </div>
                <h1 className="api-setup-title">Connect Live Data</h1>
                <p className="api-setup-subtitle">
                    Enter your free API keys to enable real-time data. Keys are stored locally in your browser.
                </p>
            </div>

            <div className="api-field">
                <div className="api-field-label">
                    <span className="api-field-name">Finnhub API Key (Required)</span>
                    <a href="https://finnhub.io/register" target="_blank" rel="noopener noreferrer" className="api-field-link">
                        Get free key <Icons.ExternalLink />
                    </a>
                </div>
                <input
                    type="text"
                    className="api-input"
                    placeholder="Enter your Finnhub API key"
                    value={keys.finnhub}
                    onChange={(e) => setKeys({ ...keys, finnhub: e.target.value })}
                />
                <p className="api-field-hint">Used for stock prices and financial news. Free tier: 60 calls/minute.</p>
            </div>

            <div className="api-field">
                <div className="api-field-label">
                    <span className="api-field-name">NewsAPI Key (Optional)</span>
                    <a href="https://newsapi.org/register" target="_blank" rel="noopener noreferrer" className="api-field-link">
                        Get free key <Icons.ExternalLink />
                    </a>
                </div>
                <input
                    type="text"
                    className="api-input"
                    placeholder="Enter your NewsAPI key"
                    value={keys.newsapi}
                    onChange={(e) => setKeys({ ...keys, newsapi: e.target.value })}
                />
                <p className="api-field-hint">Enhanced business news. Free tier: 100 requests/day. Works on localhost.</p>
            </div>

            <button className="api-submit" onClick={handleSubmit} disabled={!canSubmit}>
                Connect & Continue
            </button>

            <p style={{ textAlign: 'center', marginTop: 24, fontSize: 12, color: 'var(--text-muted)' }}>
                Sports data provided by TheSportsDB (free, no key required)
            </p>
        </div>
    );
};

const HomeScreen = ({ onNavigate }) => (
    <div className="home fade-in">
        <div className="home-hero">
            <h1 className="home-logo">Pulse</h1>
            <p className="home-tagline">Your daily brief, distilled.</p>
        </div>
        <div className="home-cards">
            <div className="category-card sports fade-in stagger-1" onClick={() => onNavigate('sports')}>
                <div className="category-icon"><Icons.Sports /></div>
                <div className="category-content">
                    <h2 className="category-title">Sports</h2>
                    <p className="category-desc">Scores, schedules, and headlines</p>
                </div>
                <div className="category-arrow">→</div>
            </div>
            <div className="category-card finance fade-in stagger-2" onClick={() => onNavigate('finance')}>
                <div className="category-icon"><Icons.Finance /></div>
                <div className="category-content">
                    <h2 className="category-title">Financial News</h2>
                    <p className="category-desc">Markets, economy, and trends</p>
                </div>
                <div className="category-arrow">→</div>
            </div>
            <div className="category-card stocks fade-in stagger-3" onClick={() => onNavigate('stocks')}>
                <div className="category-icon"><Icons.Stocks /></div>
                <div className="category-content">
                    <h2 className="category-title">Stock Market</h2>
                    <p className="category-desc">Live prices and performance</p>
                </div>
                <div className="category-arrow">→</div>
            </div>
        </div>
    </div>
);

// Sports Components
const TeamSelection = ({ selectedTeams, onAddTeam, onRemoveTeam, onContinue }) => {
    const [search, setSearch] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const searchTimeoutRef = useRef(null);

    useEffect(() => {
        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        if (search.length < 2) {
            setSearchResults([]);
            return;
        }

        setSearching(true);
        searchTimeoutRef.current = setTimeout(async () => {
            try {
                const results = await SportsAPI.searchTeams(search);
                setSearchResults(results.teams || []);
            } catch (err) {
                console.error(err);
                setSearchResults([]);
            } finally {
                setSearching(false);
            }
        }, 400);

        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, [search]);

    const isTeamSelected = (teamId) => {
        return selectedTeams.some(t => t.id === teamId);
    };

    const handleSelectTeam = (team) => {
        if (!isTeamSelected(team.idTeam)) {
            onAddTeam({
                id: team.idTeam,
                name: team.strTeam,
                abbr: team.strTeamShort || team.strTeam.substring(0, 3).toUpperCase(),
                league: team.strLeague,
                sport: team.strSport,
                badge: team.strTeamBadge,
                color: '#ff6b4a'
            });
        }
        setSearch('');
        setSearchResults([]);
    };

    return (
        <div className="sports-content fade-in">
            <div className="section-header">
                <h2 className="section-title sports">Select Your Teams</h2>
            </div>

            <div className="search-bar" style={{ marginBottom: 24 }}>
                <span className="search-icon"><Icons.Search /></span>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search for any team..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    style={{ borderColor: 'var(--sports-primary)' }}
                />
                {searching && (
                    <div style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)' }}>
                        <div className="loading-spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                    </div>
                )}
                {searchResults.length > 0 && (
                    <div className="search-results">
                        {searchResults.slice(0, 8).map(team => (
                            <div
                                key={team.idTeam}
                                className="search-result-item"
                                onClick={() => handleSelectTeam(team)}
                            >
                                {team.strTeamBadge && (
                                    <img
                                        src={team.strTeamBadge}
                                        alt=""
                                        style={{ width: 32, height: 32, objectFit: 'contain', borderRadius: 4 }}
                                    />
                                )}
                                <div className="stock-info">
                                    <div className="stock-symbol">{team.strTeam}</div>
                                    <div className="stock-name">{team.strLeague} • {team.strSport}</div>
                                </div>
                                {isTeamSelected(team.idTeam) ? (
                                    <span style={{ color: 'var(--sports-primary)' }}><Icons.Check /></span>
                                ) : (
                                    <span style={{ color: 'var(--text-muted)' }}>+ Add</span>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {selectedTeams.length > 0 && (
                <div className="selected-teams-section">
                    <div className="league-label">Your Teams ({selectedTeams.length})</div>
                    <div className="teams-grid">
                        {selectedTeams.map((team, i) => (
                            <div
                                key={team.id}
                                className="team-chip selected fade-in"
                                style={{ '--team-color': team.color }}
                            >
                                {team.badge && (
                                    <img
                                        src={team.badge}
                                        alt=""
                                        style={{ width: 28, height: 28, objectFit: 'contain', borderRadius: 4 }}
                                    />
                                )}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div className="team-abbr">{team.abbr}</div>
                                    <div className="team-league" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{team.league}</div>
                                </div>
                                <button
                                    onClick={(e) => { e.stopPropagation(); onRemoveTeam(team.id); }}
                                    style={{
                                        background: 'rgba(255,71,87,0.2)',
                                        border: 'none',
                                        borderRadius: 4,
                                        color: 'var(--negative)',
                                        width: 24,
                                        height: 24,
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: 16,
                                        fontWeight: 'bold'
                                    }}
                                >
                                    ×
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {selectedTeams.length === 0 && !search && (
                <div className="empty-state" style={{ padding: '40px 20px' }}>
                    <div className="empty-state-icon">🔍</div>
                    <p className="empty-state-text">Search for teams to add to your dashboard</p>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                        NFL, NBA, Soccer, MLB, NHL, and more
                    </p>
                </div>
            )}

            <button className="continue-btn" onClick={onContinue} disabled={selectedTeams.length === 0}>
                View Dashboard ({selectedTeams.length} team{selectedTeams.length !== 1 ? 's' : ''})
            </button>
        </div>
    );
};

const SportsDashboard = ({ selectedTeams }) => {
    const teams = selectedTeams;
    const [activeTeam, setActiveTeam] = useState(teams[0]?.id);
    const [events, setEvents] = useState({ last: [], next: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const currentTeam = teams.find(t => t.id === activeTeam) || teams[0];

    // Update activeTeam if current selection is removed
    useEffect(() => {
        if (teams.length > 0 && !teams.find(t => t.id === activeTeam)) {
            setActiveTeam(teams[0].id);
        }
    }, [teams, activeTeam]);

    const fetchTeamData = useCallback(async () => {
        if (!activeTeam) return;
        setLoading(true);
        setError(null);
        try {
            const [lastRes, nextRes] = await Promise.all([
                SportsAPI.getLastEvents(activeTeam),
                SportsAPI.getNextEvents(activeTeam)
            ]);
            setEvents({
                last: lastRes.results || [],
                next: nextRes.events || []
            });
        } catch (err) {
            setError('Failed to load team data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [activeTeam]);

    useEffect(() => {
        fetchTeamData();
    }, [fetchTeamData]);

    // Refresh every 2 minutes
    useInterval(fetchTeamData, 120000);

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        if (date.toDateString() === today.toDateString()) return 'Today';
        if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow';
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    const getResult = (event, teamId) => {
        const homeScore = parseInt(event.intHomeScore);
        const awayScore = parseInt(event.intAwayScore);
        if (isNaN(homeScore) || isNaN(awayScore)) return null;

        const isHome = event.idHomeTeam === teamId;
        const teamScore = isHome ? homeScore : awayScore;
        const opponentScore = isHome ? awayScore : homeScore;

        if (teamScore > opponentScore) return 'W';
        if (teamScore < opponentScore) return 'L';
        return 'D';
    };

    if (teams.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-icon">🏟️</div>
                <p className="empty-state-text">No teams selected yet</p>
            </div>
        );
    }

    return (
        <div className="dashboard fade-in">
            <div className="team-tabs">
                {teams.map(team => (
                    <button
                        key={team.id}
                        className={`team-tab ${activeTeam === team.id ? 'active' : ''}`}
                        onClick={() => setActiveTeam(team.id)}
                    >
                        {team.badge && (
                            <img
                                src={team.badge}
                                alt=""
                                style={{
                                    width: 20,
                                    height: 20,
                                    objectFit: 'contain',
                                    filter: activeTeam === team.id ? 'brightness(0) invert(1)' : 'none'
                                }}
                            />
                        )}
                        {team.abbr}
                    </button>
                ))}
            </div>

            {loading ? (
                <div className="loading"><div className="loading-spinner"></div></div>
            ) : error ? (
                <div className="error-state">
                    <div className="error-icon"><Icons.Alert /></div>
                    <p className="error-message">{error}</p>
                    <button className="error-retry" onClick={fetchTeamData}>Retry</button>
                </div>
            ) : (
                <>
                    {events.last.length > 0 && (
                        <div className="dashboard-section">
                            <div className="dashboard-section-title">Recent Results</div>
                            <div className="games-list">
                                {events.last.slice(0, 5).map((event, i) => {
                                    const result = getResult(event, activeTeam);
                                    return (
                                        <div key={event.idEvent} className={`game-card fade-in stagger-${i + 1}`}>
                                            <div className="game-date">{formatDate(event.dateEvent)}</div>
                                            <div className="game-info">
                                                <div className="game-teams">
                                                    {event.strHomeTeam} vs {event.strAwayTeam}
                                                </div>
                                                <div className="game-league">{event.strLeague}</div>
                                            </div>
                                            {result && (
                                                <div className={`game-result ${result === 'W' ? 'win' : result === 'L' ? 'loss' : 'draw'}`}>
                                                    {result} {event.intHomeScore}-{event.intAwayScore}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {events.next.length > 0 && (
                        <div className="dashboard-section">
                            <div className="dashboard-section-title">Upcoming Games</div>
                            <div className="games-list">
                                {events.next.slice(0, 5).map((event, i) => (
                                    <div key={event.idEvent} className={`game-card fade-in stagger-${i + 1}`}>
                                        <div className="game-date">{formatDate(event.dateEvent)}</div>
                                        <div className="game-info">
                                            <div className="game-teams">
                                                {event.strHomeTeam} vs {event.strAwayTeam}
                                            </div>
                                            <div className="game-league">{event.strLeague}</div>
                                        </div>
                                        <div className="game-time">{event.strTime?.slice(0, 5) || 'TBD'}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {events.last.length === 0 && events.next.length === 0 && (
                        <div className="empty-state">
                            <div className="empty-state-icon">📅</div>
                            <p className="empty-state-text">No recent or upcoming games found</p>
                        </div>
                    )}

                    <div className="last-updated">
                        Last updated: {new Date().toLocaleTimeString()}
                    </div>
                </>
            )}
        </div>
    );
};

const SportsSection = ({ onBack }) => {
    const [selectedTeams, setSelectedTeams] = useLocalStorage('pulse-selected-teams-v2', []);
    const [showDashboard, setShowDashboard] = useState(selectedTeams.length > 0);

    const handleAddTeam = (team) => {
        setSelectedTeams(prev => [...prev, team]);
    };

    const handleRemoveTeam = (teamId) => {
        setSelectedTeams(prev => prev.filter(t => t.id !== teamId));
    };

    return (
        <>
            <Header
                title="Sports"
                onBack={showDashboard && selectedTeams.length > 0 ? () => setShowDashboard(false) : onBack}
            />
            {showDashboard ? (
                <SportsDashboard selectedTeams={selectedTeams} />
            ) : (
                <TeamSelection
                    selectedTeams={selectedTeams}
                    onAddTeam={handleAddTeam}
                    onRemoveTeam={handleRemoveTeam}
                    onContinue={() => setShowDashboard(true)}
                />
            )}
        </>
    );
};

// Finance Section
const FinanceSection = ({ onBack, apiKeys }) => {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all');
    const [refreshing, setRefreshing] = useState(false);

    const filters = ['all', 'general', 'forex', 'crypto', 'merger'];

    const fetchNews = useCallback(async () => {
        if (!apiKeys.finnhub) {
            setError('Finnhub API key required');
            setLoading(false);
            return;
        }

        setRefreshing(true);
        try {
            const category = filter === 'all' ? 'general' : filter;
            const data = await FinnhubAPI.getMarketNews(apiKeys.finnhub, category);
            setNews(data.slice(0, 20));
            setError(null);
        } catch (err) {
            setError('Failed to load news');
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [apiKeys.finnhub, filter]);

    useEffect(() => {
        fetchNews();
    }, [fetchNews]);

    // Refresh every 2 minutes
    useInterval(fetchNews, 120000);

    const formatTime = (timestamp) => {
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);

        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString();
    };

    return (
        <>
            <Header title="Financial News" onBack={onBack} />
            <div className="finance-content fade-in">
                <div className="filter-tabs">
                    {filters.map(f => (
                        <button
                            key={f}
                            className={`filter-tab ${filter === f ? 'active' : ''}`}
                            onClick={() => setFilter(f)}
                        >
                            {f.charAt(0).toUpperCase() + f.slice(1)}
                        </button>
                    ))}
                </div>

                <div className={`refresh-indicator ${refreshing ? 'active' : ''}`}>
                    <Icons.Refresh />
                    <span>{refreshing ? 'Updating...' : 'Live updates'}</span>
                </div>

                {loading ? (
                    <div className="loading"><div className="loading-spinner"></div></div>
                ) : error ? (
                    <div className="error-state">
                        <div className="error-icon"><Icons.Alert /></div>
                        <p className="error-message">{error}</p>
                        <button className="error-retry" onClick={fetchNews}>Retry</button>
                    </div>
                ) : (
                    news.map((item, i) => (
                        <a
                            key={item.id}
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ textDecoration: 'none', color: 'inherit' }}
                        >
                            <div className={`finance-news-item fade-in stagger-${(i % 6) + 1}`}>
                                <div className="finance-news-content">
                                    <div className="finance-category-tag">{item.category}</div>
                                    <div className="news-headline">{item.headline}</div>
                                    <div className="news-meta">
                                        <span className="news-source">{item.source}</span>
                                        <span>•</span>
                                        <Icons.Clock />
                                        <span>{formatTime(item.datetime)}</span>
                                    </div>
                                </div>
                                {item.image && (
                                    <img src={item.image} alt="" className="news-image" loading="lazy" />
                                )}
                            </div>
                        </a>
                    ))
                )}

                {!loading && !error && (
                    <div className="last-updated">
                        Last updated: {new Date().toLocaleTimeString()}
                    </div>
                )}
            </div>
        </>
    );
};

// Stocks Section
const StocksSection = ({ onBack, apiKeys }) => {
    const [watchlist, setWatchlist] = useLocalStorage('pulse-watchlist', DEFAULT_STOCKS);
    const [stockData, setStockData] = useState({});
    const [stockNews, setStockNews] = useState({});
    const [search, setSearch] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [expandedStock, setExpandedStock] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const searchTimeoutRef = useRef(null);

    const fetchStockData = useCallback(async () => {
        if (!apiKeys.finnhub || watchlist.length === 0) {
            setLoading(false);
            return;
        }

        setRefreshing(true);
        try {
            const quotes = await Promise.all(
                watchlist.map(async (symbol) => {
                    try {
                        const [quote, profile] = await Promise.all([
                            FinnhubAPI.getQuote(symbol, apiKeys.finnhub),
                            FinnhubAPI.getCompanyProfile(symbol, apiKeys.finnhub)
                        ]);
                        return { symbol, quote, profile };
                    } catch {
                        return { symbol, quote: null, profile: null };
                    }
                })
            );

            const data = {};
            quotes.forEach(({ symbol, quote, profile }) => {
                if (quote && quote.c) {
                    data[symbol] = {
                        price: quote.c,
                        change: quote.d,
                        changePercent: quote.dp,
                        high: quote.h,
                        low: quote.l,
                        open: quote.o,
                        prevClose: quote.pc,
                        name: profile?.name || symbol,
                    };
                }
            });

            setStockData(data);
            setError(null);
        } catch (err) {
            setError('Failed to load stock data');
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [apiKeys.finnhub, watchlist]);

    useEffect(() => {
        fetchStockData();
    }, [fetchStockData]);

    // Refresh every 15 seconds for near real-time
    useInterval(fetchStockData, 15000);

    // Fetch news for expanded stock
    useEffect(() => {
        if (expandedStock && apiKeys.finnhub && !stockNews[expandedStock]) {
            FinnhubAPI.getCompanyNews(expandedStock, apiKeys.finnhub)
                .then(news => {
                    setStockNews(prev => ({ ...prev, [expandedStock]: news.slice(0, 3) }));
                })
                .catch(console.error);
        }
    }, [expandedStock, apiKeys.finnhub, stockNews]);

    // Search functionality
    useEffect(() => {
        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        if (search.length < 1) {
            setSearchResults([]);
            return;
        }

        searchTimeoutRef.current = setTimeout(async () => {
            try {
                const results = await FinnhubAPI.searchSymbols(search, apiKeys.finnhub);
                setSearchResults(results.result?.slice(0, 5) || []);
            } catch (err) {
                console.error(err);
            }
        }, 300);

        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, [search, apiKeys.finnhub]);

    const toggleWatchlist = (symbol) => {
        setWatchlist(prev =>
            prev.includes(symbol) ? prev.filter(s => s !== symbol) : [...prev, symbol]
        );
    };

    const addToWatchlist = (symbol) => {
        if (!watchlist.includes(symbol)) {
            setWatchlist(prev => [...prev, symbol]);
        }
        setSearch('');
        setSearchResults([]);
    };

    const formatTime = (timestamp) => {
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / 3600000);
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString();
    };

    return (
        <>
            <Header title="Stock Market" onBack={onBack} />
            <div className="stocks-content fade-in">
                <div className="search-bar">
                    <span className="search-icon"><Icons.Search /></span>
                    <input
                        type="text"
                        className="search-input"
                        placeholder="Search stocks or ETFs..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value.toUpperCase())}
                    />
                    {searchResults.length > 0 && (
                        <div className="search-results">
                            {searchResults.map(result => (
                                <div
                                    key={result.symbol}
                                    className="search-result-item"
                                    onClick={() => addToWatchlist(result.symbol)}
                                >
                                    <div className="stock-info">
                                        <div className="stock-symbol">{result.symbol}</div>
                                        <div className="stock-name">{result.description}</div>
                                    </div>
                                    {watchlist.includes(result.symbol) ? (
                                        <Icons.Check />
                                    ) : (
                                        <span style={{ color: 'var(--text-muted)' }}>+ Add</span>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="watchlist-header">
                    <div className="watchlist-title">Your Watchlist</div>
                    <div className={`refresh-indicator ${refreshing ? 'active' : ''}`} style={{ padding: 0 }}>
                        <Icons.Refresh />
                        <span>{refreshing ? 'Updating' : 'Live'}</span>
                    </div>
                </div>

                {loading ? (
                    <div className="loading"><div className="loading-spinner"></div></div>
                ) : error ? (
                    <div className="error-state">
                        <div className="error-icon"><Icons.Alert /></div>
                        <p className="error-message">{error}</p>
                        <button className="error-retry" onClick={fetchStockData}>Retry</button>
                    </div>
                ) : (
                    <div className="stocks-grid">
                        {watchlist.map((symbol, i) => {
                            const data = stockData[symbol];
                            if (!data) return null;

                            const isExpanded = expandedStock === symbol;
                            const news = stockNews[symbol] || [];

                            return (
                                <div
                                    key={symbol}
                                    className={`stock-card fade-in stagger-${(i % 6) + 1} ${isExpanded ? 'expanded' : ''}`}
                                    onClick={() => setExpandedStock(isExpanded ? null : symbol)}
                                >
                                    <div className="stock-main">
                                        <div className="stock-info">
                                            <div className="stock-symbol">{symbol}</div>
                                            <div className="stock-name">{data.name}</div>
                                        </div>
                                        <div className="stock-price-info">
                                            <div className="stock-price">${data.price?.toFixed(2)}</div>
                                            <div className={`stock-change ${data.change >= 0 ? 'positive' : 'negative'}`}>
                                                {data.change >= 0 ? <Icons.TrendUp /> : <Icons.TrendDown />}
                                                {data.change >= 0 ? '+' : ''}{data.change?.toFixed(2)} ({data.changePercent?.toFixed(2)}%)
                                            </div>
                                        </div>
                                        <div
                                            className="stock-star active"
                                            onClick={(e) => { e.stopPropagation(); toggleWatchlist(symbol); }}
                                        >
                                            <Icons.Star />
                                        </div>
                                    </div>
                                    {isExpanded && (
                                        <div className="stock-news">
                                            {news.length > 0 ? (
                                                news.map(item => (
                                                    <div key={item.id} className="stock-news-item">
                                                        <Icons.Clock />
                                                        <a href={item.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
                                                            {item.headline} • {formatTime(item.datetime)}
                                                        </a>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="stock-news-item">Loading news...</div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                {watchlist.length === 0 && !loading && (
                    <div className="empty-state">
                        <div className="empty-state-icon">📈</div>
                        <p className="empty-state-text">Search and add stocks to your watchlist</p>
                    </div>
                )}

                {!loading && !error && watchlist.length > 0 && (
                    <div className="last-updated">
                        Last updated: {new Date().toLocaleTimeString()} • Refreshes every 15s
                    </div>
                )}
            </div>
        </>
    );
};

// ============================================
// MAIN APP
// ============================================

const App = () => {
    const [currentScreen, setCurrentScreen] = useState('home');
    const [apiKeys, setApiKeys] = useState(getApiKeys);
    const [showApiSetup, setShowApiSetup] = useState(!apiKeys.finnhub);

    const handleApiComplete = (keys) => {
        setApiKeys(keys);
        setShowApiSetup(false);
    };

    const renderScreen = () => {
        if (showApiSetup) {
            return (
                <>
                    <Header />
                    <ApiSetup onComplete={handleApiComplete} initialKeys={apiKeys} />
                </>
            );
        }

        switch (currentScreen) {
            case 'sports':
                return <SportsSection onBack={() => setCurrentScreen('home')} />;
            case 'finance':
                return <FinanceSection onBack={() => setCurrentScreen('home')} apiKeys={apiKeys} />;
            case 'stocks':
                return <StocksSection onBack={() => setCurrentScreen('home')} apiKeys={apiKeys} />;
            default:
                return (
                    <>
                        <Header showSettings onSettings={() => setShowApiSetup(true)} />
                        <HomeScreen onNavigate={setCurrentScreen} />
                    </>
                );
        }
    };

    return (
        <>
            <style>{styles}</style>
            <div className="app">{renderScreen()}</div>
        </>
    );
};

// Mount the app
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
