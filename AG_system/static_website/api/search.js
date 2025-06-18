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

async function getRelatedPhotos(answerText, answerId, apiKey) {
  try {
    console.log(`Getting photos for answer: ${answerText.substring(0, 50)}...`);
    
    // Get embedding for the answer text
    const answerEmbedding = await getEmbeddingViaRest(answerText, apiKey);
    
    // Initialize Pinecone for your existing index
    const pinecone = new Pinecone({ apiKey });
    const index = pinecone.Index('adas-memory-qa-poc'); // Changed to capital I
    
    // First, test if photo-captions namespace exists at all
    console.log("Testing photo-captions namespace accessibility...");
    const testQuery = await index.query({
      vector: answerEmbedding,
      topK: 2,
      includeMetadata: true,
      namespace: 'photo-captions'
      // No filter first - just see if anything is there
    });
    
    console.log(`Test query found ${testQuery.matches?.length || 0} total photos in namespace`);
    if (testQuery.matches?.length > 0) {
      console.log("Sample metadata keys:", Object.keys(testQuery.matches[0].metadata || {}));
      console.log("Sample prompt_type value:", testQuery.matches[0].metadata?.prompt_type);
    }
    
    // Search for MOMENT captions in photo-captions namespace
    console.log("Searching for MOMENT captions...");
    const momentResults = await index.query({
      vector: answerEmbedding,
      topK: 4, // Get extra for filtering
      includeMetadata: true,
      namespace: 'photo-captions',
      filter: {
        prompt_type: 'MOMENT'
      }
    });
    
    // Search for CONTEXTUAL captions in photo-captions namespace  
    console.log("Searching for CONTEXTUAL captions...");
    const contextualResults = await index.query({
      vector: answerEmbedding,
      topK: 4, // Get extra for filtering
      includeMetadata: true,
      namespace: 'photo-captions',
      filter: {
        prompt_type: 'CONTEXTUAL'
      }
    });
    
    console.log(`Found ${momentResults.matches?.length || 0} MOMENT matches, ${contextualResults.matches?.length || 0} CONTEXTUAL matches`);
    
    // Log some details about what we found
    if (momentResults.matches?.length > 0) {
      console.log("First MOMENT result metadata:", Object.keys(momentResults.matches[0].metadata || {}));
    }
    if (contextualResults.matches?.length > 0) {
      console.log("First CONTEXTUAL result metadata:", Object.keys(contextualResults.matches[0].metadata || {}));
    }
    
    // Process MOMENT results (take top 2, no threshold)
    const momentPhotos = momentResults.matches
      ?.slice(0, 2) // Always take top 2, regardless of score
      .map((match, index) => ({
        photo_id: match.id,
        thumbnail_url: match.metadata?.wordpress_thumbnail,
        modal_url: match.metadata?.wordpress_url || match.metadata?.wordpress_thumbnail,
        caption_moment: match.metadata?.caption_text, // The MOMENT caption
        caption_full: match.metadata?.caption_text, // Could add full description later
        relevance_score: match.score,
        source_date: match.metadata?.photo_date,
        position: index,
        caption_type: 'MOMENT'
      })) || [];
    
    // Process CONTEXTUAL results (take top 2, no threshold)
    const contextualPhotos = contextualResults.matches
      ?.slice(0, 2) // Always take top 2, regardless of score
      .map((match, index) => ({
        photo_id: match.id,
        thumbnail_url: match.metadata?.wordpress_thumbnail,
        modal_url: match.metadata?.wordpress_url || match.metadata?.wordpress_thumbnail,
        caption_moment: match.metadata?.caption_text, // The CONTEXTUAL caption
        caption_full: match.metadata?.caption_text,
        relevance_score: match.score,
        source_date: match.metadata?.photo_date,
        position: index + 2, // Continue position numbering
        caption_type: 'CONTEXTUAL'
      })) || [];
    
    // Combine and sort by relevance score
    const allPhotos = [...momentPhotos, ...contextualPhotos]
      .sort((a, b) => b.relevance_score - a.relevance_score)
      .map((photo, index) => ({
        ...photo,
        position: index // Reorder positions based on final sort
      }));
    
    console.log(`Returning ${allPhotos.length} photos (${momentPhotos.length} MOMENT, ${contextualPhotos.length} CONTEXTUAL)`);
    
    return allPhotos;
    
  } catch (error) {
    console.error('Photo matching error:', error);
    console.error('Error details:', {
      message: error.message,
      stack: error.stack,
      answerText: answerText?.substring(0, 50)
    });
    return []; // Graceful degradation - return empty array if photo search fails
  }
}

export default async function handler(req, res) {
  console.log("--- Ada's Spark Search Handler ---");

  // CORS Headers
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

    // Query Q&A index using SDK (default namespace)
    const pinecone = new Pinecone({ apiKey });
    const index = pinecone.Index('adas-memory-qa-poc');
    
    const searchResponse = await index.query({
      vector: queryVector,
      topK: parseInt(limit, 10),
      includeMetadata: true
      // No namespace specified = searches default namespace with Q&A pairs
    });

    console.log("Q&A search completed, matches:", searchResponse.matches?.length || 0);

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
              console.log(`Getting photos for answer ${i + 1} of question: ${metadata.question_text}`);
              answers[i].related_photos = await getRelatedPhotos(
                answers[i].answer_text,
                answers[i].answer_id,
                apiKey
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