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

async function getRelatedPhotos(answerText, answerId, apiKey, limit = 4) {
  try {
    // Get embedding for the answer text
    const answerEmbedding = await getEmbeddingViaRest(answerText, apiKey);
    
    // Initialize Pinecone for photo index
    const pinecone = new Pinecone({ apiKey });
    const photoIndex = pinecone.index('adas-photos-index'); // You'll need to create this index
    
    // Query photo captions
    const photoResults = await photoIndex.query({
      vector: answerEmbedding,
      topK: limit * 2, // Get extra for filtering
      includeMetadata: true,
      filter: {
        // Add any filters you need
      }
    });
    
    // Process and filter results
    const photos = photoResults.matches
      ?.filter(match => match.score > 0.55) // Relevance threshold
      .slice(0, limit)
      .map((match, index) => ({
        photo_id: match.id,
        thumbnail_url: match.metadata?.thumbnail_url,
        modal_url: match.metadata?.modal_url || match.metadata?.thumbnail_url,
        caption: match.metadata?.caption_moment || match.metadata?.caption,
        caption_full: match.metadata?.caption_full,
        relevance_score: match.score,
        source_date: match.metadata?.creation_date,
        position: index
      })) || [];
    
    return photos;
    
  } catch (error) {
    console.error('Photo matching error:', error);
    return []; // Graceful degradation
  }
}

export default async function handler(req, res) {
  console.log("--- Ada's Spark Search Handler ---");

  // CORS Headers
  
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

// Process results - Enhanced with photo matching
    const results = await Promise.all(
      searchResponse.matches?.map(async (match) => {
        const metadata = match.metadata || {};
        
        // Parse the answers_json string into actual objects
        let answers = [];
        if (metadata.answers_json) {
          try {
            answers = JSON.parse(metadata.answers_json);
            
            // Add photos to each answer
            for (let i = 0; i < answers.length; i++) {
              answers[i].related_photos = await getRelatedPhotos(
                answers[i].answer_text,
                answers[i].answer_id,
                apiKey,
                4
              );
            }
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
          answers: answers // Now includes related_photos for each answer
        };
      }) || []
    );

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
