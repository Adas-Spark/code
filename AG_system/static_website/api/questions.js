// Create new file: api/questions.js
export default async function handler(req, res) {
  // Strict CORS - only allow your domain  
  const allowedOrigins = [
    'https://adas-spark.org',
    'https://www.adas-spark.org',
    'http://localhost:8000'  // For local development
  ];

  const origin = req.headers.origin;
  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  } else {
    res.setHeader('Access-Control-Allow-Origin', 'https://adas-spark.org');
  }
  
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { Pinecone } = await import('@pinecone-database/pinecone');
    const pinecone = new Pinecone({ apiKey: process.env.PINECONE_API_KEY });
    const index = pinecone.index('adas-memory-qa-poc');
    
    const questions = await getDistinctRandomQuestions(index);
    
    return res.status(200).json({ 
      questions: questions.map((q, index) => ({
        id: `q${index + 1}`,
        text: q
      }))
    });
    
  } catch (error) {
    console.error('Error fetching questions:', error);
    // Fallback to static questions
    return res.status(200).json({ 
      questions: [
        { id: 'q1', text: 'What was Ada like as a person?' },
        { id: 'q2', text: 'What were Ada\'s favorite activities?' },
        { id: 'q3', text: 'What did Ada teach her parents?' }
      ]
    });
  }
}

async function getDistinctRandomQuestions(index, maxAttempts = 2) {
  const SIMILARITY_THRESHOLD = 0.8;
  
  for (let attempt = 0; attempt <= maxAttempts; attempt++) {
    console.log(`Attempt ${attempt + 1} to get distinct questions`);
    
    // Get random questions by querying with random vectors
    const randomQueries = await Promise.all([
      index.query({ 
        vector: generateRandomVector(), 
        topK: 1, 
        includeMetadata: true 
      }),
      index.query({ 
        vector: generateRandomVector(), 
        topK: 1, 
        includeMetadata: true 
      }),
      index.query({ 
        vector: generateRandomVector(), 
        topK: 1, 
        includeMetadata: true 
      })
    ]);
    
    // Extract questions and their vectors
    const questionData = randomQueries
      .map(result => {
        const match = result.matches?.[0];
        if (match?.metadata?.question_text) {
          return {
            text: match.metadata.question_text,
            vector: null // We'll need to get embeddings for similarity check
          };
        }
        return null;
      })
      .filter(Boolean);
    
    if (questionData.length < 3) {
      console.log(`Only found ${questionData.length} questions, continuing...`);
      continue;
    }
    
    // Get embeddings for similarity comparison
    const questionsWithEmbeddings = await Promise.all(
      questionData.map(async (q) => ({
        ...q,
        vector: await getEmbeddingViaRest(q.text, process.env.PINECONE_API_KEY)
      }))
    );
    
    // Check similarity between all pairs
    const similarities = [];
    for (let i = 0; i < questionsWithEmbeddings.length; i++) {
      for (let j = i + 1; j < questionsWithEmbeddings.length; j++) {
        const similarity = cosineSimilarity(
          questionsWithEmbeddings[i].vector,
          questionsWithEmbeddings[j].vector
        );
        similarities.push({
          pair: [i, j],
          similarity: similarity,
          questions: [questionsWithEmbeddings[i].text, questionsWithEmbeddings[j].text]
        });
      }
    }
    
    // Check if any pair is too similar
    const tooSimilar = similarities.some(s => s.similarity > SIMILARITY_THRESHOLD);
    
    if (!tooSimilar) {
      console.log('Found distinct questions:', questionsWithEmbeddings.map(q => q.text));
      return questionsWithEmbeddings.map(q => q.text);
    } else {
      console.log(`Questions too similar (max similarity: ${Math.max(...similarities.map(s => s.similarity)).toFixed(3)}), resampling...`);
    }
  }
  
  // If we couldn't find distinct questions after max attempts, return what we have
  console.log(`Max attempts reached, returning potentially similar questions`);
  const fallbackQueries = await Promise.all([
    index.query({ vector: generateRandomVector(), topK: 1, includeMetadata: true }),
    index.query({ vector: generateRandomVector(), topK: 1, includeMetadata: true }),
    index.query({ vector: generateRandomVector(), topK: 1, includeMetadata: true })
  ]);
  
  return fallbackQueries
    .map(result => result.matches?.[0]?.metadata?.question_text)
    .filter(Boolean)
    .slice(0, 3);
}

// Reuse your existing embedding function
async function getEmbeddingViaRest(text, apiKey) {
  const fetch = (await import('node-fetch')).default;
  
  const url = 'https://api.pinecone.io/embed';
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Api-Key': apiKey,
    'x-pinecone-api-version': '2025-04'
  };
  const body = JSON.stringify({
    model: 'llama-text-embed-v2',
    inputs: [{ text: text }],
    parameters: {
      input_type: 'query',
      dimension: 1024
    }
  });

  const response = await fetch(url, {
    method: 'POST',
    headers: headers,
    body: body
  });

  const responseData = await response.json();

  if (!response.ok) {
    throw new Error(`Embedding API failed: ${response.status}`);
  }

  return responseData.data[0].values;
}

function generateRandomVector() {
  // Generate random 1024-dimensional vector (normalized)
  const vector = Array.from({ length: 1024 }, () => Math.random() * 2 - 1);
  
  // Normalize the vector
  const magnitude = Math.sqrt(vector.reduce((sum, val) => sum + val * val, 0));
  return vector.map(val => val / magnitude);
}

function cosineSimilarity(vectorA, vectorB) {
  if (vectorA.length !== vectorB.length) {
    throw new Error('Vectors must have the same length');
  }
  
  let dotProduct = 0;
  let magnitudeA = 0;
  let magnitudeB = 0;
  
  for (let i = 0; i < vectorA.length; i++) {
    dotProduct += vectorA[i] * vectorB[i];
    magnitudeA += vectorA[i] * vectorA[i];
    magnitudeB += vectorB[i] * vectorB[i];
  }
  
  magnitudeA = Math.sqrt(magnitudeA);
  magnitudeB = Math.sqrt(magnitudeB);
  
  if (magnitudeA === 0 || magnitudeB === 0) {
    return 0;
  }
  
  return dotProduct / (magnitudeA * magnitudeB);
}
