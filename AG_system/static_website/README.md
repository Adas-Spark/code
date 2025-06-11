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
-In `app.js`, update the `API_CONFIG` object to point to your deployed Vercel API endpoint:
-
+In `app.js`, the API is configured to use Ada's custom domain:
 ```javascript
-// Located in app.js - Line ~2
+// Located in app.js
 const API_CONFIG = {
-    baseUrl: 'https://your-project-name.vercel.app/api', // IMPORTANT: Replace with your actual Vercel deployment URL
+    baseUrl: 'https://memories.adas-spark.org/api', // Custom domain for stable API endpoint
     endpoints: {
-        search: '/search' // This creates: https://your-project-name.vercel.app/api/search
+        search: '/search',
+        questions: '/questions' // Example: endpoint for dynamic questions
     },
     timeout: 30000 // API request timeout in milliseconds
 };
 ```
 
-**Important Notes:**
-- Replace `your-project-name` with your actual Vercel project name
-- The full URL is required because the static front-end (WP Engine) calls the API (Vercel) - this is a cross-origin request
-- Your Vercel API must include proper CORS headers (see "CORS Configuration" section below)
+**Benefits of Custom Domain (`memories.adas-spark.org`):**
+- **No `baseUrl` Updates Needed**: The `API_CONFIG.baseUrl` in `app.js` remains constant. The custom domain always points to the latest production Vercel deployment.
+- **Stable Endpoint**: Provides a reliable and professional API endpoint.
+- **Simplified Workflow**: Eliminates the need to update and redeploy frontend code (`app.js`) solely for Vercel deployment URL changes.
 
-When you add new API endpoints (like `api/questions.js`):
+**Workflow for Adding/Modifying API Endpoints:**
 
-1. **Create the endpoint file** in your local `api/` directory
-2. **Deploy to Vercel**: `vercel --prod`
-3. **Note the new deployment URL** from Vercel output
-4. **Update `app.js`**: Change `API_CONFIG.baseUrl` to the new Vercel URL
-5. **Commit the URL update**: `git add app.js && git commit -m "Update API URL"`
-6. **Upload to WP Engine**: Only upload the updated `app.js` (NOT the API files)
-7. **Clear WP Engine cache** and test
+When you add new API endpoints (e.g., `api/new_feature.js`) or modify existing ones:
 
-**Important**: API files (`api/*.js`) run on Vercel, not WP Engine. Only upload static files (`index.html`, `styles.css`, `app.js`) to WP Engine.
+1.  **Develop API Endpoint**:
    *   Create or modify the endpoint file in your local `api/` directory (e.g., `api/new_feature.js`).
    *   Implement the necessary logic.
+
+2.  **Update Frontend (`app.js`) - If Necessary**:
    *   **For New Endpoints**: If this is a new endpoint that the frontend needs to call, add its path to the `API_CONFIG.endpoints` object in `app.js`.
        ```javascript
        // Example update in app.js
        const API_CONFIG = {
            baseUrl: 'https://memories.adas-spark.org/api',
            endpoints: {
                search: '/search',
                questions: '/questions',
                newFeature: '/new_feature' // Add new endpoint path
            },
            // ...
        };
        ```
    *   **Update Frontend Logic**: Modify `app.js` to call the new or updated API endpoint (e.g., add a new method in `apiService` or update an existing one).
+
+3.  **Commit Changes**:
    *   Commit changes to the API file(s) and `app.js` (if modified).
        ```bash
        git add api/ app.js # Or specific files
        git commit -m "Update/Add API endpoint and integrate with frontend"
        ```
+
+4.  **Deploy API to Vercel**:
    *   Run `vercel --prod` from your project root (typically the `static_website` directory if it's linked to your Vercel project).
    *   Your custom domain (e.g., `https://memories.adas-spark.org/api/new_feature`) will automatically point to the latest version of the new/updated function.
+
+5.  **Deploy Frontend (`app.js`) to WP Engine - If Modified**:
    *   If `app.js` was changed in Step 2, upload the updated `app.js` to your WP Engine subdirectory (e.g., `/memory-engine/`).
+
+6.  **Test**:
    *   Clear browser cache and any relevant server-side caches (e.g., WP Engine cache).
    *   Thoroughly test the new or modified functionality.
+
+**Important**: API files (e.g., `api/search.js`, `api/questions.js`) are deployed to and run on Vercel. Only static frontend files (`index.html`, `styles.css`, `app.js`) are uploaded to WP Engine.
 
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

The current setup is designed to handle Cross-Origin Resource Sharing (CORS) correctly:
- The frontend, embedded via an iframe, is served from `https://adas-spark.org/memory-engine/`.
- API calls are made from this frontend to `https://memories.adas-spark.org/api`.

Since `adas-spark.org` (where the iframe is hosted) and `memories.adas-spark.org` (the API) are treated as different origins by browsers, CORS is necessary.

**How CORS is Handled:**
1.  **Vercel API Functions (`api/search.js`, `api/questions.js`):**
    *   These functions dynamically set the `Access-Control-Allow-Origin` header.
    *   They check if the request's `Origin` header is in a predefined list of `allowedOrigins` (e.g., `https://adas-spark.org`, `https://www.adas-spark.org`, `http://localhost:8000`).
    *   If the origin is allowed, the `Access-Control-Allow-Origin` header is set to that specific origin.
    *   If the origin is not in the list, the functions currently default to setting `Access-Control-Allow-Origin` to `https://adas-spark.org`.
    *   They also set `Access-Control-Allow-Methods` (e.g., `POST, GET, OPTIONS`) and `Access-Control-Allow-Headers` (e.g., `Content-Type`).
    *   Preflight `OPTIONS` requests are handled to return `200 OK` with these headers.

2.  **`vercel.json` Configuration:**
    *   The `vercel.json` file also defines default headers for paths matching `/api/(.*)`, including an `Access-Control-Allow-Origin` set to `https://adas-spark.org`. While function-level headers often take precedence for dynamic values, this provides a baseline.

This configuration allows the browser to make requests from the embedded frontend on `adas-spark.org` to the API on `memories.adas-spark.org`. The custom domain for the Vercel API provides a stable endpoint, simplifying this configuration.

**Example from `api/search.js` and `api/questions.js`:**
```javascript
export default async function handler(req, res) { // Simplified example for README
  // This code is part of your Vercel serverless functions
  const allowedOrigins = [
    'https://adas-spark.org',
    'https://www.adas-spark.org',
    'http://localhost:8000'  // For local development
  ];
  
  const origin = req.headers.origin;
  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }
  // Reflects methods used by search (POST) and questions (GET) APIs, and vercel.json
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  // ... rest of your API logic
}
```

**Testing CORS:**
```bash
-# Test your API endpoint directly
-curl -X POST https://your-project.vercel.app/api/search \
+# Test your API endpoint directly (replace with your actual custom domain if different)
+curl -X POST https://memories.adas-spark.org/api/search \
  -H "Content-Type: application/json" \
-  -H "Origin: https://yourwpsite.com" \
+  -H "Origin: https://adas-spark.org" \
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

**Manual Deployment Process for Frontend Files:**
1.  **Update Files Locally**: Make changes to `app.js`, `index.html`, `styles.css` as needed.
2.  **Commit Changes**: `git add . && git commit -m "Your descriptive commit message"`
3.  **Connect via SFTP to WP Engine**:
    ```bash
    sftp -P <YOUR_SFTP_PORT> <YOUR_SFTP_USERNAME>@<YOUR_SFTP_HOST>
    ```
    > **Security Warning**: Storing full SFTP credentials or commands with usernames directly in a public README is a security risk. Consider using SSH keys, environment variables for scripts, or a secure password manager. The command above is provided for informational purposes based on your input.
4.  **Navigate to Directory**: Once connected, change to your target directory:
    ```sftp
    cd memory-engine
    ```
5.  **Upload Changed Files**:
    ```sftp
    put app.js
    put index.html
    # etc., for any other changed frontend files
    ```
6.  **Test**: Visit `https://adas-spark.org/memory-engine/` and the WordPress page where it's embedded. Clear browser cache and WP Engine cache if necessary.

**SFTP Shortcut (Optional):**
You can add an alias to your shell configuration file (e.g., `~/.zshrc` or `~/.bashrc`) for easier SFTP access:
```bash
# Add to ~/.zshrc or ~/.bashrc
alias adasftp='sftp -P <YOUR_SFTP_PORT> <YOUR_SFTP_USERNAME>@<YOUR_SFTP_HOST>'
```
Then you can just type `adasftp` to connect.

## Embedding in WordPress (via iframe)

Once the static front-end is deployed to its subdirectory on WP Engine:

1. **Create or edit a page** in your WordPress admin where you want to embed the search interface
2. **Use an HTML block** to insert the following iframe. This setup is currently in use:

```html
<div style="width: 100%; max-width: 1200px; margin: 0 auto;">
    <iframe 
        src="https://adas-spark.org/memory-engine/index.html"
        width="100%" 
        height="800px"
        frameborder="0"
        scrolling="auto"
        allow="clipboard-read; clipboard-write"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        title="Ada's Spark Memory Engine"
        style="border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    </iframe>
</div>
```

**Benefits of this iframe setup:**
- **No Cross-Origin Issues for Embedding**: Since the iframe `src` (`adas-spark.org/memory-engine/`) is on the same primary domain as the WordPress page embedding it, browser security restrictions for iframe embedding are simpler. (Note: API calls from the iframe's content to `memories.adas-spark.org` are still cross-origin and handled by CORS as described above).
- **Stable Iframe URL**: The `src` attribute of the iframe points to a stable path on WP Engine and doesn't need updates when only the backend API (on Vercel) is redeployed.
- **Professional Integration**: Allows the memory engine to be seamlessly presented within the main `adas-spark.org` website.

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

- **Desktop**: Chrome 60+, Firefox 60+, Safari 12+, Edge 79+

## Performance Features

- **Mobile Caching Addressed**: Includes `<meta http-equiv="Cache-Control" content="must-revalidate">` in `index.html` to help ensure users get updated versions of files while still allowing caching.
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

## Mobile Caching Solution

**Problem**: Mobile browsers (and desktop browsers sometimes) can aggressively cache static files like `app.js`, `styles.css`, and `index.html`. This means that after deploying updates to these files on WP Engine, users might continue to see an outdated version of the memory engine.

**Solution Implemented**:
The `index.html` file includes a meta tag to instruct browsers on how to handle caching:
```html
<meta http-equiv="Cache-Control" content="must-revalidate">
```

**How `must-revalidate` works**:
- The browser is allowed to cache the file.
- On subsequent visits, before using the cached version, the browser *must* check with the server (revalidate) to see if the file has changed.
- If the file has changed on the server, the browser downloads the new version.
- If the file has not changed, the server confirms this, and the browser uses its cached version (which is fast).

**Result**: This strikes a balance between performance (allowing caching) and ensuring users eventually receive updates (eventual consistency). It doesn't guarantee immediate updates for all users due to various layers of caching (browser, network, WP Engine's own caching), but it significantly improves the situation.

## Troubleshooting

### Mobile Caching Issues

-   **Symptom**: Mobile users see old version, desktop users see new version.
-   **Test**: Try incognito mode - if it shows new version, it's a caching issue.
-   **Solution**: Add `must-revalidate` meta tag (already implemented in `index.html`).
-   **Prevention**: Hard refresh after uploads (Ctrl+Shift+R or Cmd+Shift+R). Clear WP Engine cache if applicable.

### SFTP Upload Issues

-   **Connection**: Use port `2222` with `-P` flag (capital P).
    ```bash
    sftp -P 2222 adasspark-joelswenson@adasspark.sftp.wpengine.com
    ```
    > **Security Note**: Be cautious about storing full SFTP credentials in public documentation.
-   **Directory**: Navigate to `memory-engine` folder after connecting.
    ```sftp
    cd memory-engine
    ```
-   **Files**: Upload only frontend files (`app.js`, `index.html`, `styles.css`).
    ```sftp
    put app.js
    ```
-   **Verification**: Check file timestamps after upload.

### API Endpoint Changes

-   **Custom Domain**: `memories.adas-spark.org` always points to the latest Vercel deployment.
-   **No Updates Needed**: Frontend code (`app.js`) doesn't need to change when only the API is redeployed, thanks to the stable custom domain.
-   **Testing**: Check Network tab in browser dev tools for API calls to verify the correct endpoint is being used and responses are as expected.

### CORS Issues (Less Common with Current Setup)

-   **Current Setup Avoids Most Issues**:
    *   Frontend loads from `adas-spark.org/memory-engine/` (WP Engine).
    *   API calls go to `memories.adas-spark.org/api` (Vercel with custom domain).
    *   The Vercel API functions (`api/search.js`, `api/questions.js`) and `vercel.json` are configured to set `Access-Control-Allow-Origin` headers, allowing requests from `https://adas-spark.org`.
-   **If Issues Arise**:
    *   **Symptom**: Browser console shows errors like "Access-Control-Allow-Origin missing".
    *   **Check**:
        1.  Ensure `memories.adas-spark.org` is correctly serving CORS headers (inspect response headers in Network tab).
        2.  Verify that `https://adas-spark.org` (and `https://www.adas-spark.org`) is in the `allowedOrigins` list in your Vercel API functions and/or `vercel.json`.
        3.  Ensure preflight `OPTIONS` requests are handled correctly by the API, returning a `200 OK` with appropriate CORS headers.

### Iframe and Embedding Issues

-   **Iframe Not Loading**:
    *   Verify the `src` attribute in your WordPress iframe HTML block points to the correct URL: `https://adas-spark.org/memory-engine/index.html`.
    *   Check browser console for any security policy errors related to iframes (e.g., `X-Frame-Options` if misconfigured, though your `vercel.json` sets this to `DENY` for API routes, which is good for API security but not directly related to the WP Engine iframe source).
-   **Mixed Content Warnings**: Ensure all resources (API endpoint, static files on WP Engine, CDN links, and the main WordPress site) are served over HTTPS.

### General Debugging Tips

-   **Browser Developer Tools**: Use the Console for JavaScript errors, the Network tab for API request/response details, and the Elements tab to inspect HTML/CSS.
-   **Enable Verbose Logging in `app.js`**: Temporarily add more `console.log` statements in `app.js` during development to trace execution flow and variable states.
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
