# Ada's Spark Memory Engine - Static Front-End

A modern, responsive web interface for searching Ada's memories using semantic search. Built as a decoupled architecture: static front-end (deployed to WP Engine) + serverless API (deployed to Vercel).

**Production Architecture**: Static files served from WP Engine subdirectory → embedded via iframe in WordPress → API calls to Vercel serverless functions → Pinecone vector search.

## Features

- **Modern Design**: Clean, responsive interface following Ada's Spark branding
- **Accessibility**: WCAG AA compliant with proper ARIA labels, keyboard navigation, and screen reader support
- **Vue.js Integration**: Interactive components with reactive search functionality
- **Decoupled API**: Communicates with separate Vercel backend for search operations
- **Error Handling**: Comprehensive error states and user feedback for API interactions
- **Mobile Responsive**: Optimized for all device sizes
- **Performance**: Optimized loading with CDN resources and efficient rendering
- **Embeddable**: Designed for embedding within WordPress sites via iframes

## Project Structure

```
AG_system/static_website/
├── index.html          # Main HTML structure for the standalone search interface
├── styles.css          # CSS styling and responsive design
├── app.js             # Vue.js app and vanilla JavaScript functionality
├── api/
│   ├── search.js       # Main search API endpoint
│   └── questions.js    # Dynamic example questions API endpoint
├── README.md          # This documentation
├── prompt.md          # Prompt for recreating this app (if applicable)
└── vercel.json        # Vercel configuration for API deployment
API Integration**: Perform a search to ensure front-end → API communication works

### WordPress Integration - Final Step
1. **Create Page**: Add new page in WordPress admin
2. **Add Iframe**: Insert HTML block with iframe pointing to your static site
3. **Test Embedded Version**: Verify the iframe loads and functions properly
4. **Adjust Height**: Modify iframe height as needed for your content

### Troubleshooting Checklist
- [ ] API returns 200 status when tested directly
- [ ] Browser console shows no CORS errors
- [ ] Static files load without 404 errors
- [ ] Iframe displays content (check browser security settings)
- [ ] Search functionality works end-to-end

## Backend Overview

This static front-end communicates with a dedicated backend API to perform semantic searches and retrieve Ada's memories.

**Purpose**: The backend API handles:
- Receiving search queries from this front-end
- Generating vector embeddings using Pinecone's `llama-text-embed-v2` model
- Querying the Pinecone vector index (`adas-memory-qa-poc`) to find relevant memories
- Securely managing the Pinecone API key and other sensitive configurations
- Formatting and returning search results to the front-end

**Technology**: Built as serverless functions (Node.js) deployed on **Vercel** with **Pinecone** as the external service.

**Endpoint**: The front-end interacts with the backend via the `/api/search` endpoint.

**Current Implementation Note**: Due to a bug in Pinecone Node.js SDK v6.0.1, the backend uses direct REST API calls for generating embeddings while still using the SDK for index queries. See "Known Issues" section below.

## API Integration

### 1. API Configuration
In `app.js`, update the `API_CONFIG` object to point to your deployed Vercel API endpoint:

```javascript
// Located in app.js - Line ~2
const API_CONFIG = {
    baseUrl: 'https://your-project-name.vercel.app/api', // IMPORTANT: Replace with your actual Vercel deployment URL
    endpoints: {
        search: '/search' // This creates: https://your-project-name.vercel.app/api/search
    },
    timeout: 30000 // API request timeout in milliseconds
};
```

**Important Notes:**
- Replace `your-project-name` with your actual Vercel project name
- The full URL is required because the static front-end (WP Engine) calls the API (Vercel) - this is a cross-origin request
- Your Vercel API must include proper CORS headers (see "CORS Configuration" section below)

When you add new API endpoints (like `api/questions.js`):

1. **Create the endpoint file** in your local `api/` directory
2. **Deploy to Vercel**: `vercel --prod`
3. **Note the new deployment URL** from Vercel output
4. **Update `app.js`**: Change `API_CONFIG.baseUrl` to the new Vercel URL
5. **Commit the URL update**: `git add app.js && git commit -m "Update API URL"`
6. **Upload to WP Engine**: Only upload the updated `app.js` (NOT the API files)
7. **Clear WP Engine cache** and test

**Important**: API files (`api/*.js`) run on Vercel, not WP Engine. Only upload static files (`index.html`, `styles.css`, `app.js`) to WP Engine.

### 2. Expected API Contract

**Request from Front-End to Back-End:**
```json
POST /api/search
{
    "query": "What was Ada like as a person?",
    "limit": 5,
    "timestamp": 1640995200000
}
```

**Response Expected by Front-End from Back-End:**
```json
// Successful response with results
{
    "results": [
        {
            "question_id": "Q1",
            "question_text": "What was Ada like as a person?",
            "category": "character",
            "score": 0.95,
            "answers": [
                {
                    "answer_id": "Q1A1",
                    "answer_text": "Ada was a beacon of unwavering spirit...",
                    "source_post_id": "post-123",
                    "source_date": "2023-05-15"
                }
            ]
        }
    ]
}

// Response for no results or low similarity
{
    "results": [],
    "message": "No similar questions found. Try rephrasing your question or click one of the example questions.",
    "lowScore": true
}

// Error response
{
    "error": "Internal server error: Failed to generate a valid query embedding."
}
```

### 3. Enable Real API
Ensure the `performSearch()` method in `app.js` is configured to call `apiService.searchMemories(this.searchQuery)` and not a mock function.

## CORS Configuration (Critical for Production)

Your Vercel API **must** include proper CORS headers since your static front-end (WP Engine) will be making cross-origin requests to your API (Vercel).

**In your `api/search.js` file:**

```javascript
export default async function handler(req, res) {
  // CORS Headers - REQUIRED for production
  const allowedOrigins = [
    'https://yourwpsite.com',           // Your main WordPress site
    'https://yoursubdomain.wpengine.com', // WP Engine staging if applicable
    'http://localhost:8000',            // Local development
  ];
  
  const origin = req.headers.origin;
  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Your existing API logic...
}
```

**Testing CORS:**
```bash
# Test your API endpoint directly
curl -X POST https://your-project.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -H "Origin: https://yourwpsite.com" \
  -d '{"query":"test","limit":5}'
```

## Deployment

### 1. Backend API Deployment (Vercel)
Your backend Node.js search API should be deployed to Vercel with:
- Configure Vercel environment variables to securely store your `PINECONE_API_KEY`
- Note the production URL Vercel provides (e.g., `https://your-project-name.vercel.app`)
- Ensure your `vercel.json` includes the function timeout configuration

### 2. Static Front-End Deployment (WP Engine Subdirectory)
**Before deploying the front-end files:**
- Ensure `API_CONFIG.baseUrl` in `app.js` points to your live Vercel API endpoint
- Upload `index.html`, `styles.css`, `app.js` to your designated subdirectory on WP Engine
- No build step is required for these static front-end files

## Embedding in WordPress (via iframe)

Once the static front-end is deployed to its subdirectory on WP Engine:

1. **Create or edit a page** in your WordPress admin where you want to embed the search interface
2. **Use an HTML block** to insert an iframe:

```html
<iframe 
    src="https://yourwpsite.com/ada-search/index.html" 
    width="100%" 
    height="600px" 
    style="border:none;"
    title="Ada's Memory Search">
</iframe>
```

3. **Adjust the `src`** to the correct public URL of your `index.html` in the WP Engine subdirectory
4. **Adjust `height`** as needed for your content

## Known Issues & Workarounds

### Pinecone SDK v6.0.1 Embedding Bug
**Issue**: The Pinecone Node.js SDK v6.0.1 has a bug that prevents embedding generation from working correctly.

**Symptoms**: 
- API calls to generate embeddings fail or return unexpected responses
- Error messages related to embedding generation

**Current Workaround**: The backend API (`api/search.js`) uses direct REST API calls for embedding generation while still using the SDK for index queries.

**Implementation**: See the `getEmbeddingViaRest()` function in `api/search.js` which bypasses the SDK for embeddings.

**Status**: Monitor Pinecone SDK releases for a fix. When resolved, the implementation can be simplified to use SDK-only calls.

### Testing the Workaround
```javascript
// Current working approach in search.js:
queryVector = await getEmbeddingViaRest(query, pineconeApiKey); // Direct REST
const searchResponse = await index.query({ vector: queryVector }); // SDK for query
```

## Local Development

1. **Navigate to the static website directory:**
   ```bash
   cd AG_system/static_website
   ```

2. **Local Development**: For testing API interactions, a local web server is recommended:
   ```bash
   # Python
   python -m http.server 8000
   
   # Node.js (http-server)
   npx http-server
   
   # PHP
   php -S localhost:8000
   ```

3. **API Development**: Ensure your Vercel API is deployed and accessible, or use a mock server for local API development.

## Browser Support

- **Modern Browsers**: Chrome 60+, Firefox 60+, Safari 12+, Edge 79+
- **Mobile**: iOS Safari 12+, Chrome Mobile 60+
- **Progressive Enhancement**: Basic functionality without JavaScript

## Performance Features

- **CDN Dependencies**: Vue.js, Font Awesome, and Google Fonts loaded from CDN
- **API Call Optimization**: Minimized data requested and processed
- **Debounced Search**: Prevents excessive API calls to the Vercel backend
- **Connection Monitoring**: Handles offline/online states for better UX
- **Lazy Loading**: For images and non-critical resources

## Accessibility Features

- **Keyboard Navigation**: Full keyboard support with focus indicators
- **Screen Readers**: Proper ARIA labels and semantic HTML
- **Color Contrast**: WCAG AA compliant color ratios
- **Motion Preferences**: Respects `prefers-reduced-motion`
- **Font Scaling**: Responsive to user font size preferences

## Security Considerations

- **Input Sanitization**: User inputs are sanitized in `app.js` before being sent to the Vercel API
- **XSS Prevention**: Vue.js provides inherent XSS protection; ensure safe DOM manipulations
- **HTTPS**: Ensure WordPress site, static front-end path, and Vercel API all use HTTPS
- **API Key Security**: Pinecone API key must NEVER be in front-end code; stored securely as Vercel environment variable
- **CORS**: Properly configured to allow requests only from authorized domains
- **Content Security Policy**: Consider CSP headers for enhanced security

## Troubleshooting

### Common CORS Issues
- ❌ **Error**: "CORS policy: No 'Access-Control-Allow-Origin' header"
  - ✅ **Solution**: Add proper CORS headers in your Vercel function
- ❌ **Error**: "CORS policy: Request header field content-type is not allowed"  
  - ✅ **Solution**: Add 'Content-Type' to 'Access-Control-Allow-Headers'

### Common Deployment Issues
- **API Endpoint Misconfiguration**: Double-check `API_CONFIG.baseUrl` in `app.js` matches your Vercel URL exactly
- **API Timeouts**: Check `API_CONFIG.timeout` and Vercel function execution limits (`maxDuration: 30` in `vercel.json`)
- **Iframe Issues**: Verify `src` attribute is correct and check browser console for iframe policy errors
- **Mixed Content Warnings**: Ensure all resources (API, static files, CDNs, WordPress site) use HTTPS
- **Caching**: After deploying updates, use hard refresh (Ctrl+Shift+R) to clear browser cache. Also clear WP Engine caches.

### Debug Mode
Enable console logging by setting:
```javascript
const DEBUG = true; // Add to top of app.js
```

## Customization

### Branding Colors
Main brand colors defined in CSS:
```css
:root {
    --primary-orange: #ffa726;
    --primary-blue: #4285f4;
    --text-dark: #2c3e50;
    --background: #fafafa;
}
```

### Example Questions
Update in `app.js` data section:
```javascript
exampleQuestions: [
    { id: 'q1', text: 'Your custom question here' },
    // Add more questions...
]
```

## Monitoring and Analytics

- **Front-end interactions** are tracked via `analytics.trackEvent` in `app.js`
- **Backend API logging** should be configured separately on the Vercel platform
- Built-in analytics tracking for search performance and user interactions

## Future Enhancements

- **Service Worker**: For offline functionality
- **Progressive Web App**: Add manifest.json for installability
- **Advanced Search**: Filters, categories, date ranges
- **Voice Search**: Web Speech API integration
- **Dark Mode**: User preference toggle

## License

This project is created in memory of Ada Rose Swenson. Please use responsibly and with respect for Ada's legacy.

---

**Questions or Issues?** Contact the development team or create an issue in the project repository.
