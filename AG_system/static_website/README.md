# Ada's Spark Memory Engine - Static Website

A modern, responsive, and accessible web interface for searching Ada's memories using semantic search powered by Pinecone vector database.

## Features

- **Modern Design**: Clean, responsive interface following Ada's Spark branding
- **Accessibility**: WCAG compliant with proper ARIA labels, keyboard navigation, and screen reader support
- **Vue.js Integration**: Interactive components with reactive search functionality
- **Error Handling**: Comprehensive error states and user feedback
- **Progressive Enhancement**: Works with JavaScript disabled (basic functionality)
- **Mobile Responsive**: Optimized for all device sizes
- **Performance**: Optimized loading with CDN resources and efficient rendering

## Project Structure

```
AG_system/static_website/
├── index.html          # Main HTML structure
├── styles.css          # CSS styling and responsive design
├── app.js             # Vue.js app and vanilla JavaScript functionality
├── README.md          # This documentation
├── prompt.md          # Prompt for recreating this app
└── Screenshot...png   # Original mockup reference
```

## Quick Start

1. **Navigate to the static website directory:**
   ```bash
   cd AG_system/static_website
   ```

2. **Local Development**: Simply open `index.html` in a web browser
3. **Web Server**: Serve files using any static web server:
   ```bash
   # Python
   python -m http.server 8000
   
   # Node.js (http-server)
   npx http-server
   
   # PHP
   php -S localhost:8000
   ```

## API Integration

### Current State
The application currently uses mock data for development. To connect to your Pinecone serverless function:

### 1. Update API Configuration
In `app.js`, update the `API_CONFIG` object:

```javascript
const API_CONFIG = {
    baseUrl: 'https://your-actual-api-endpoint.vercel.app/api', // Your endpoint
    endpoints: {
        search: '/search'
    },
    timeout: 30000
};
```

### 2. Expected API Contract

**Request Format:**
```json
POST /api/search
{
    "query": "What was Ada like as a person?",
    "limit": 5,
    "timestamp": 1640995200000
}
```

**Response Format:**
```json
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
```

### 3. Enable Real API
In `app.js`, replace the mock call in the `performSearch()` method:

```javascript
// Replace this line:
const mockResponse = await this.getMockResponse(this.searchQuery);

// With this line:
const response = await apiService.searchMemories(this.searchQuery);
```

## Deployment Options

### Static Hosting (Recommended)
- **Netlify**: Drag and drop the folder or connect to Git
- **Vercel**: `vercel --prod` in the project directory
- **GitHub Pages**: Push to a repository and enable Pages
- **AWS S3**: Upload files and configure static website hosting

### CDN Deployment
All dependencies are loaded from CDN, making deployment simple:
- Vue.js 3 (unpkg)
- Font Awesome 6 (cdnjs)
- Google Fonts (fonts.googleapis.com)

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

### Styling
- Modify `styles.css` for visual changes
- Uses CSS Grid and Flexbox for responsive layouts
- Includes dark mode ready variables

## Browser Support

- **Modern Browsers**: Chrome 60+, Firefox 60+, Safari 12+, Edge 79+
- **Progressive Enhancement**: Basic functionality without JavaScript
- **Mobile**: iOS Safari 12+, Chrome Mobile 60+

## Performance Features

- **Lazy Loading**: Images and non-critical resources
- **Debounced Search**: Prevents excessive API calls
- **Connection Monitoring**: Handles offline/online states
- **Error Recovery**: Automatic retry logic and user feedback
- **Analytics Ready**: Built-in event tracking (extend as needed)

## Accessibility Features

- **Keyboard Navigation**: Full keyboard support with focus indicators
- **Screen Readers**: Proper ARIA labels and semantic HTML
- **Color Contrast**: WCAG AA compliant color ratios
- **Motion Preferences**: Respects `prefers-reduced-motion`
- **Font Scaling**: Responsive to user font size preferences

## Security Considerations

- **Input Sanitization**: User inputs are sanitized before API calls
- **XSS Prevention**: Safe HTML rendering practices
- **HTTPS Only**: Configure your server to enforce HTTPS
- **Content Security Policy**: Add CSP headers for enhanced security

## Monitoring and Analytics

The application includes built-in analytics tracking:

```javascript
// Track search performance
analytics.trackSearch(query, resultCount, responseTime);

// Track user interactions
analytics.trackEvent('example_question_clicked', { question: text });

// Track errors
analytics.trackError(error, context);
```

Integrate with your preferred analytics service (Google Analytics, Mixpanel, etc.).

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure your API endpoint allows requests from your domain
2. **API Timeouts**: Check the timeout setting in `API_CONFIG`
3. **Mobile Issues**: Test on actual devices, not just browser dev tools
4. **Font Loading**: Verify Google Fonts are accessible in your region

### Debug Mode
Enable console logging by setting:
```javascript
const DEBUG = true; // Add to top of app.js
```

## Future Enhancements

- **Service Worker**: For offline functionality
- **Progressive Web App**: Add manifest.json for installability
- **Advanced Search**: Filters, categories, date ranges
- **Voice Search**: Web Speech API integration
- **Dark Mode**: User preference toggle
- **Internationalization**: Multi-language support

## License

This project is created in memory of Ada Rose Swenson. Please use responsibly and with respect for Ada's legacy.

---

**Questions or Issues?** Contact the development team or create an issue in the project repository.