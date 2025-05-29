  # First Promopt

  Create a modern, responsive, and accessible HTML5 static webpage that includes the following elements:
  - It uses Vue from CDN for widgets and interactivity. And vanilla JavaScript for additional functionality.
  - It uses CSS for styling.
  - The interface is based on the mockup provided in the image @static_website/Screenshot 2025-05-28 at 18.08.42.png 
  - Polish the mockup so that it is more visually appealing and user-friendly.
  - The static page should include a method to call a serveless pythonn function to query a pincecone database as we prototyped in @pinecone_poc.ipynb 
  - The code should be well-structued, DRY and follow best practices.
  - Putt all the page files in @static_website/ folder.

  # LLM's refined prompt:
  
  Create Ada's Spark Memory Engine - Complete Static Website

  I need you to create a modern, responsive, and accessible HTML5 static webpage for "Ada's Spark: Hope Against Childhood Cancer" - a memory search interface. This should be a complete
  production-ready website.

  Project Requirements:

  1. Technology Stack:
    - HTML5 with semantic structure and accessibility features
    - Vue.js 3 from CDN for reactive components
    - Modern CSS with responsive design (no frameworks - custom CSS only)
    - Vanilla JavaScript for additional functionality
    - Font Awesome icons and Google Fonts integration
  2. Design Specifications:
    - Based on Ada's Spark branding (warm yellow/orange sun logo with text)
    - Clean, modern interface with subtle shadows and rounded corners
    - Mobile-first responsive design
    - Color scheme: Primary orange (#ffa726), blue (#4285f4), dark text (#2c3e50)
    - Typography: Inter for UI, Crimson Text for headings
  3. Core Features to Implement:
    - Header with Ada's Spark logo (sun icon + "ada's SPARK" text)
    - Main title: "Ada's Spark: Hope Against Childhood Cancer"
    - Descriptive text about the organization and Ada's memory
    - Interactive example questions that populate search when clicked:
        - "What was Ada like as a person?"
      - "What was Ada's favorite meal?"
      - "What did Ada teach her parents?"
    - Search input with rounded styling and arrow button
    - Results section showing:
        - "You asked: [query]" with similar question found
      - Answer display area
      - Navigation between multiple answers if available
      - Source date and similarity score
    - Loading states, error handling, and empty states
  4. Technical Requirements:
    - WCAG AA accessibility compliance
    - Full keyboard navigation support
    - Screen reader optimization with ARIA labels
    - Responsive breakpoints (mobile, tablet, desktop)
    - API integration ready for Pinecone serverless function
    - Mock data for immediate testing
    - Error handling and timeout management
    - Analytics tracking hooks
  5. API Integration:
    - Configure for serverless function endpoint
    - Expected request: {"query": "text", "limit": 5}
    - Expected response: {"results": [{"question_id", "question_text", "score", "answers": []}]}
    - Include comprehensive error handling
    - Timeout configuration (30 seconds)
    - Connection monitoring
  6. File Structure:
  static_website/
  ├── index.html
  ├── styles.css  
  ├── app.js
  └── README.md
  7. Specific Implementation Details:
    - Vue.js app mounted on #app element
    - Debounced search to prevent excessive API calls
    - Smooth scrolling to results section
    - Multiple answer pagination with numbered buttons
    - Date formatting utilities
    - Input sanitization for security
    - Progressive enhancement (works without JavaScript)
  8. Content Guidelines:
    - Use the exact organizational description provided
    - Include Ada's motto: "Life isn't about waiting for the storm to pass...It's about learning to dance in the rain"
    - Maintain respectful, memorial tone throughout
    - Include source attribution and date display for answers
  9. Performance & UX:
    - CSS animations with reduced motion preferences
    - Intersection Observer for scroll animations
    - Service worker ready architecture
    - CDN-only dependencies (no local libraries)
    - Optimized for Core Web Vitals
  10. Documentation:
    - Comprehensive README with setup instructions
    - API integration guide
    - Deployment options (Netlify, Vercel, GitHub Pages)
    - Customization guidelines
    - Troubleshooting section

  Deliverables:
  - Complete, production-ready static website
  - All files properly structured and commented
  - Mock data that demonstrates full functionality
  - Documentation for deployment and maintenance

  Quality Standards:
  - Follow modern web development best practices
  - Ensure cross-browser compatibility (Chrome 60+, Firefox 60+, Safari 12+)
  - Implement proper error boundaries and user feedback
  - Include comprehensive input validation and sanitization
  - Write clean, maintainable, well-documented code

  Create this as a complete package that can be immediately deployed to any static hosting service and easily connected to a Pinecone API backend when ready.