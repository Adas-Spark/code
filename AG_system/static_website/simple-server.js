const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8000;

// Mock data
const mockQuestions = {
  questions: [
    { id: 'q1', text: 'What made Ada laugh?' },
    { id: 'q2', text: 'How did Ada show bravery?' },
    { id: 'q3', text: 'Tell me about Ada\'s spirit' }
  ]
};

const mockSearchResults = {
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
        },
        {
          photo_id: 'photo_003',
          thumbnail_url: 'https://picsum.photos/250/180?random=3',
          modal_url: 'https://picsum.photos/800/600?random=3',
          caption_moment: 'Family cuddles on the couch',
          relevance_score: 0.68,
          source_date: '2023-05-08',
          position: 2
        }
      ]
    }]
  }]
};

// MIME types
const mimeTypes = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  console.log(`${req.method} ${req.url}`);

  // Handle API endpoints
  if (req.url === '/api/questions' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(mockQuestions));
    return;
  }

  if (req.url === '/api/search' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    req.on('end', () => {
      console.log('Search request body:', body);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(mockSearchResults));
    });
    return;
  }

  // Serve static files
  let filePath = '.' + req.url;
  if (filePath === './') {
    filePath = './index.html';
  }

  const extname = String(path.extname(filePath)).toLowerCase();
  const contentType = mimeTypes[extname] || 'application/octet-stream';

  fs.readFile(filePath, (error, content) => {
    if (error) {
      if (error.code === 'ENOENT') {
        res.writeHead(404);
        res.end('404 Not Found');
      } else {
        res.writeHead(500);
        res.end('Server Error: ' + error.code);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

server.listen(PORT, () => {
  console.log(`Simple test server running at http://localhost:${PORT}`);
  console.log('Available endpoints:');
  console.log('  GET  /api/questions');
  console.log('  POST /api/search');
});