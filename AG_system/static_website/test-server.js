// test-server.js
const express = require('express');
const path = require('path');
const app = express();

// Serve static files
app.use(express.static('.'));

// Mock API endpoints
app.use(express.json());

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
          answer_text: 'Ada was a beacon of unwavering spirit and resilience...',
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

// Mock questions endpoint
app.get('/api/questions', (req, res) => {
  res.json({
    questions: [
      { id: 'q1', text: 'What made Ada laugh?' },
      { id: 'q2', text: 'How did Ada show bravery?' },
      { id: 'q3', text: 'Tell me about Ada\'s spirit' }
    ]
  });
});

app.listen(8000, () => {
  console.log('Test server running at http://localhost:8000');
});