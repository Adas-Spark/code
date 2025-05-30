import { Pinecone } from '@pinecone-database/pinecone';

async function getEmbeddingViaRest(text, apiKey) {
  console.log("Getting embedding for:", text.substring(0, 50) + "...");
  
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
    throw new Error(`Embedding API failed: ${response.status} - ${JSON.stringify(responseData)}`);
  }

  return responseData.data[0].values;
}

export default async function handler(req, res) {
  console.log("--- Ada's Spark Search Handler ---");

  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { query, limit = 5 } = req.body;

    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }

    const apiKey = process.env.PINECONE_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: 'Server configuration error' });
    }

    console.log("Processing query:", query);

    // Get embedding using REST API workaround
    const queryVector = await getEmbeddingViaRest(query, apiKey);
    console.log("Embedding generated, dimension:", queryVector.length);

    // Query index using SDK
    const pinecone = new Pinecone({ apiKey });
    const index = pinecone.index('adas-memory-qa-poc');
    
    const searchResponse = await index.query({
      vector: queryVector,
      topK: parseInt(limit, 10),
      includeMetadata: true
    });

    console.log("Search completed, matches:", searchResponse.matches?.length || 0);

    // Process results - FIXED: Parse answers_json
    const results = searchResponse.matches?.map(match => {
      const metadata = match.metadata || {};
      
      // Parse the answers_json string into actual objects
      let answers = [];
      if (metadata.answers_json) {
        try {
          answers = JSON.parse(metadata.answers_json);
        } catch (error) {
          console.error("Error parsing answers_json:", error);
          answers = [];
        }
      }
      
      return {
        question_id: metadata.question_id,
        question_text: metadata.question_text,
        category: metadata.category,
        score: match.score,
        answers: answers // Now this will be an array of answer objects
      };
    }) || [];

    // Check similarity threshold
    const SIMILARITY_THRESHOLD = 0.6;
    if (results.length === 0 || (results[0] && results[0].score < SIMILARITY_THRESHOLD)) {
      return res.status(200).json({
        results: [],
        message: "No similar questions found. Try rephrasing your question or click one of the example questions.",
        lowScore: true
      });
    }

    return res.status(200).json({ results });

  } catch (error) {
    console.error('Search error:', error);
    return res.status(500).json({ 
      error: 'Internal server error: ' + error.message 
    });
  }
}
