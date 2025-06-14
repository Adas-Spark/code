const express = require('express');
const path = require('path');
const app = express();

// Serve static files
app.use(express.static('.'));

// Parse JSON bodies
app.use(express.json());

// Mock questions endpoint
app.get('/api/questions', (req, res) => {
  console.log('Questions endpoint called');
  res.json({
    questions: [
      { id: 'q1', text: 'What made Ada laugh?' },
      { id: 'q2', text: 'How did Ada show bravery?' },
      { id: 'q3', text: 'Tell me about Ada\'s spirit' }
    ]
  });
});

// Mock search endpoint
app.post('/api/search', (req, res) => {
  console.log('Search request:', req.body);
  
  // Mock response with photos
  setTimeout(() => {
    res.json({
      results: [{
        question_id: 'Q1',
        question_text: 'What was Ada like as a person?',
        category: 'character',
        score: 0.95,
        answers: [{
          answer_id: 'Q1A1',
          answer_text: 'Ada was a beacon of unwavering spirit and resilience. Even when faced with the intense pain and nausea of chemotherapy, she\'d insist, sometimes literally yelling, "I just want to play" and then proceed to do exactly that.',
          source_post_id: 'post-123',
          source_date: '2023-05-15',
          related_photos: [
            {
              photo_id: 'photo_001',
              thumbnail_url: 'https://picsum.photos/250/180?random=1',
              modal_url: 'https://picsum.photos/800/600?random=1',
              caption_moment: 'A moment of pure joy',
              caption_full: 'Ada laughing during a sunny afternoon at the park',
              relevance_score: 0.85,
              source_date: '2023-05-15',
              position: 0
            },
            {
              photo_id: 'photo_002',
              thumbnail_url: 'https://picsum.photos/250/180?random=2',
              modal_url: 'https://picsum.photos/800/600?random=2',
              caption_moment: 'Discovering a butterfly',
              relevance_score: 0.72,
              source_date: '2023-05-10',
              position: 1
            }
          ]
        }]
      }]
    });
  }, 500);
});

// Handle all other routes by serving index.html
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

const PORT = 8000;
app.listen(PORT, () => {
  console.log(`Test server running at http://localhost:${PORT}`);
  console.log('Available endpoints:');
  console.log('  GET  /api/questions');
  console.log('  POST /api/search');
});