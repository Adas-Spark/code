// ===== CONFIGURATION =====
const API_CONFIG = {
    baseUrl: 'https://adas-living-story-1s5ryuv7i-joel-swensons-projects.vercel.app/api',
    endpoints: {
        search: '/search'
    },
    timeout: 30000
};

// ===== UTILITY FUNCTIONS =====
const utils = {
    /**
     * Debounce function to limit API calls
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Format date string to human-readable format
     */
    formatDate(dateString) {
        if (!dateString) return 'Unknown date';

        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    },

    /**
     * Sanitize user input for safety
     */
    sanitizeInput(input) {
        if (typeof input !== 'string') return '';
        return input.trim().replace(/[<>]/g, '');
    },

    /**
     * Generate unique ID for tracking
     */
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
};

// ===== API SERVICE =====
const apiService = {
    /**
     * Make API request with timeout and error handling
     */
    async makeRequest(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new Error('Request timeout. Please try again.');
            }

            throw error;
        }
    },

    /**
     * Search for answers using the Pinecone API
     */
    async searchMemories(query, limit = 5) {
        const url = `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.search}`;

        const requestBody = {
            query: utils.sanitizeInput(query),
            limit: Math.min(Math.max(limit, 1), 10), // Ensure limit is between 1-10
            timestamp: Date.now() // For request tracking
        };

        return await this.makeRequest(url, {
            method: 'POST',
            body: JSON.stringify(requestBody)
        });
    }
};

// ===== ANALYTICS & TRACKING =====
const analytics = {
    /**
     * Track user interactions (can be extended with real analytics)
     */
    trackEvent(eventName, data = {}) {
        console.log('Analytics Event:', eventName, data);

        // Example: Send to analytics service
        // gtag('event', eventName, data);
        // or: mixpanel.track(eventName, data);
    },

    trackSearch(query, resultCount, responseTime) {
        this.trackEvent('search_performed', {
            query_length: query.length,
            result_count: resultCount,
            response_time_ms: responseTime
        });
    },

    trackError(error, context = {}) {
        this.trackEvent('error_occurred', {
            error_message: error.message,
            error_type: error.name,
            ...context
        });
    }
};

// ===== VUE.JS APPLICATION =====
const { createApp } = Vue;

createApp({
    data() {
        return {
            // Search state
            searchQuery: '',
            lastSearchQuery: '',
            searchResults: [],
            selectedAnswer: null,
            selectedAnswerIndex: 0,

            // UI state
            isLoading: false,
            showResults: false,
            error: null,

            // Example questions from the mockup
            exampleQuestions: [
                {
                    id: 'q1',
                    text: 'What was Ada like as a person?'
                },
                {
                    id: 'q2',
                    text: 'What was Ada\'s favorite meal?'
                },
                {
                    id: 'q3',
                    text: 'What did Ada teach her parents?'
                }
            ],

            // Performance tracking
            searchStartTime: null
        };
    },

    computed: {
        /**
         * Check if search input is valid
         */
        isSearchValid() {
            return this.searchQuery.trim().length >= 3;
        },

        /**
         * Get formatted search results count
         */
        resultsCount() {
            return this.searchResults.length;
        }
    },

    methods: {
        /**
         * Populate search input with example question
         */
        populateQuestion(questionText) {
            this.searchQuery = questionText;
            this.clearResults();

            analytics.trackEvent('example_question_clicked', {
                question: questionText
            });

            // Auto-focus search input after population
            this.$nextTick(() => {
                const searchInput = document.querySelector('.search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            });
        },

        /**
         * Perform search operation
         */
        async performSearch() {
            if (!this.isSearchValid || this.isLoading) {
                return;
            }

            this.isLoading = true;
            this.error = null;
            this.searchStartTime = Date.now();
            this.lastSearchQuery = this.searchQuery;

            try {
                // Simulate API call for development
                const response = await apiService.searchMemories(this.searchQuery);

                // Uncomment the line below when your API is ready
                // const response = await apiService.searchMemories(this.searchQuery);

                this.handleSearchSuccess(response);

            } catch (error) {
                this.handleSearchError(error);
            } finally {
                this.isLoading = false;
            }
        },

        /**
         * Handle successful search response
         */
        handleSearchSuccess(response) {
            const responseTime = Date.now() - this.searchStartTime;

            // Check for low score message
            if (response.lowScore && response.message) {
                this.error = response.message;
                this.showResults = true;
                return;
            }

            // Process the response based on expected API structure
            this.searchResults = response.results || [];

            if (this.searchResults.length > 0) {
                // Select the first answer of the best matching question
                const firstResult = this.searchResults[0];
                if (firstResult.answers && firstResult.answers.length > 0) {
                    this.selectAnswer(firstResult.answers[0], 0);
                }
            }

            this.showResults = true;

            // Track successful search
            analytics.trackSearch(
                this.lastSearchQuery,
                this.searchResults.length,
                responseTime
            );

            // Scroll to results
            this.$nextTick(() => {
                const resultsSection = document.querySelector('.results-section');
                if (resultsSection) {
                    resultsSection.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        },

        /**
         * Handle search errors
         */
        handleSearchError(error) {
            console.error('Search error:', error);

            this.error = this.getErrorMessage(error);
            this.searchResults = [];
            this.selectedAnswer = null;
            this.showResults = true;

            analytics.trackError(error, {
                query: this.lastSearchQuery,
                search_context: 'primary_search'
            });
        },

        /**
         * Get user-friendly error message
         */
        getErrorMessage(error) {
            if (error.message.includes('timeout')) {
                return 'Request timed out. Please check your connection and try again.';
            }

            if (error.message.includes('HTTP error')) {
                return 'Service temporarily unavailable. Please try again in a moment.';
            }

            if (error.message.includes('Failed to fetch')) {
                return 'Unable to connect to the service. Please check your internet connection.';
            }

            return 'Something went wrong. Please try again or contact support if the problem persists.';
        },

        /**
         * Select a specific answer for display
         */
        selectAnswer(answer, index) {
            this.selectedAnswer = answer;
            this.selectedAnswerIndex = index;

            analytics.trackEvent('answer_selected', {
                answer_index: index,
                answer_id: answer.answer_id || 'unknown'
            });
        },

        /**
         * Clear search results and UI state
         */
        clearResults() {
            this.searchResults = [];
            this.selectedAnswer = null;
            this.selectedAnswerIndex = 0;
            this.showResults = false;
            this.error = null;
        },

        /**
         * Clear error message
         */
        clearError() {
            this.error = null;
        },

        /**
         * Format date using utility function
         */
        formatDate(dateString) {
            return utils.formatDate(dateString);
        },

        /**
         * Mock API response for development/testing
         * Remove this when connecting to real API
         */
        async getMockResponse(query) {
            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 1500));

            // Mock response based on query
            const mockResults = [
                {
                    question_id: 'Q1',
                    question_text: 'What was Ada like as a person?',
                    category: 'character',
                    score: 0.95,
                    answers: [
                        {
                            answer_id: 'Q1A1',
                            answer_text: 'Ada was a beacon of unwavering spirit and resilience. Even when faced with the intense pain and nausea of chemotherapy, she\'d insist, sometimes literally yelling, "I just want to play" and then proceed to do exactly that. Her determination was infectious - she never let her illness define her or limit her joy. Ada approached every day with curiosity and excitement, finding wonder in the smallest moments and bringing light to everyone around her.',
                            source_post_id: 'post-123',
                            source_date: '2023-05-15'
                        },
                        {
                            answer_id: 'Q1A2',
                            answer_text: 'What struck everyone about Ada was her incredible empathy and emotional intelligence. Despite being so young and dealing with her own challenges, she had an remarkable ability to sense when others needed comfort. She would offer hugs, share her favorite toys, or simply sit quietly with someone who was sad. Her compassion knew no bounds.',
                            source_post_id: 'post-124',
                            source_date: '2023-06-02'
                        },
                        {
                            answer_id: 'Q1A3',
                            answer_text: 'Ada had this amazing ability to find joy in everything. Whether it was a new book, a butterfly outside her window, or a silly joke, she approached life with pure delight. Her laughter was contagious, and even during her toughest days, she could find something to smile about.',
                            source_post_id: 'post-125',
                            source_date: '2023-06-10'
                        }
                    ]
                }
            ];

            return { results: mockResults };
        }
    },

    mounted() {
        // Set up keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            // Focus search input when pressing '/' key
            if (event.key === '/' && !event.target.matches('input, textarea')) {
                event.preventDefault();
                const searchInput = document.querySelector('.search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // Clear search when pressing Escape
            if (event.key === 'Escape') {
                if (this.showResults) {
                    this.clearResults();
                    this.searchQuery = '';
                }
            }
        });

        // Track page load
        analytics.trackEvent('page_loaded', {
            timestamp: Date.now(),
            user_agent: navigator.userAgent
        });

        // Set up periodic connection check (optional)
        // this.setupConnectionMonitoring();
    },

    /**
     * Set up connection monitoring for better UX
     */
    setupConnectionMonitoring() {
        let isOnline = navigator.onLine;

        window.addEventListener('online', () => {
            if (!isOnline) {
                isOnline = true;
                // Could show a "Connection restored" message
                analytics.trackEvent('connection_restored');
            }
        });

        window.addEventListener('offline', () => {
            if (isOnline) {
                isOnline = false;
                analytics.trackEvent('connection_lost');

                // Show offline message if user tries to search
                if (this.isLoading) {
                    this.error = 'You appear to be offline. Please check your connection and try again.';
                    this.isLoading = false;
                }
            }
        });
    }
}).mount('#app');

// ===== ADDITIONAL VANILLA JS ENHANCEMENTS =====

/**
 * Intersection Observer for scroll animations
 */
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth reveal animations for elements
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements that should animate in
    const animatedElements = document.querySelectorAll('.example-question-btn, .search-container');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

/**
 * Service Worker registration for offline functionality (optional)
 */
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment when you have a service worker file
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered'))
        //     .catch(error => console.log('SW registration failed'));
    });
}
