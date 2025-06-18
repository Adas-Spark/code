import { Pinecone } from '@pinecone-database/pinecone';

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
    throw new Error(`Embedding API failed: ${response.status} - ${JSON.stringify(responseData)}`);
  }

  return responseData.data[0].values;
}

export default async function handler(req, res) {
  // CORS Headers
  const allowedOrigins = [
    'https://adas-spark.org',
    'https://www.adas-spark.org',
    'http://localhost:8000'
  ];

  const origin = req.headers.origin;
  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  } else {
    res.setHeader('Access-Control-Allow-Origin', 'https://adas-spark.org');
  }

  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const debugResult = {
      step: 'starting',
      timestamp: new Date().toISOString(),
      errors: [],
      logs: []
    };

    // Test text - same as what would come from an answer
    const testAnswerText = "Based on her family's eulogy, three words that describe Ada are happy, energetic, and strong-willed";
    debugResult.logs.push(`Testing with answer text: ${testAnswerText.substring(0, 50)}...`);
    
    const apiKey = process.env.PINECONE_API_KEY;
    if (!apiKey) {
      debugResult.errors.push('PINECONE_API_KEY not found');
      return res.status(500).json(debugResult);
    }
    debugResult.logs.push('✅ API key found');

    // Step 1: Generate embedding
    debugResult.step = 'generating_embedding';
    try {
      const embedding = await getEmbeddingViaRest(testAnswerText, apiKey);
      debugResult.logs.push(`✅ Embedding generated (dimension: ${embedding.length})`);
    } catch (error) {
      debugResult.errors.push(`Embedding failed: ${error.message}`);
      return res.status(500).json(debugResult);
    }

    // Step 2: Connect to Pinecone
    debugResult.step = 'connecting_pinecone';
    try {
      const pinecone = new Pinecone({ apiKey });
      const index = pinecone.Index('adas-memory-qa-poc');
      debugResult.logs.push('✅ Connected to Pinecone index');
    } catch (error) {
      debugResult.errors.push(`Pinecone connection failed: ${error.message}`);
      return res.status(500).json(debugResult);
    }

    // Step 3: Test namespace query
    debugResult.step = 'testing_namespace';
    try {
      const pinecone = new Pinecone({ apiKey });
      const index = pinecone.Index('adas-memory-qa-poc');
      const embedding = await getEmbeddingViaRest(testAnswerText, apiKey);
      
      const testQuery = await index.query({
        vector: embedding,
        topK: 3,
        includeMetadata: true,
        namespace: 'photo-captions'
      });
      
      debugResult.logs.push(`✅ Namespace query returned ${testQuery.matches?.length || 0} results`);
      
      if (testQuery.matches && testQuery.matches.length > 0) {
        debugResult.logs.push(`✅ Sample photo ID: ${testQuery.matches[0].id}`);
        debugResult.logs.push(`✅ Sample metadata keys: ${Object.keys(testQuery.matches[0].metadata || {}).join(', ')}`);
      }
    } catch (error) {
      debugResult.errors.push(`Namespace query failed: ${error.message}`);
      return res.status(500).json(debugResult);
    }

    // Step 4: Test filters
    debugResult.step = 'testing_filters';
    try {
      const pinecone = new Pinecone({ apiKey });
      const index = pinecone.Index('adas-memory-qa-poc');
      const embedding = await getEmbeddingViaRest(testAnswerText, apiKey);
      
      const momentResults = await index.query({
        vector: embedding,
        topK: 2,
        includeMetadata: true,
        namespace: 'photo-captions',
        filter: { prompt_type: 'MOMENT' }
      });
      
      const contextualResults = await index.query({
        vector: embedding,
        topK: 2,
        includeMetadata: true,
        namespace: 'photo-captions',
        filter: { prompt_type: 'CONTEXTUAL' }
      });
      
      debugResult.logs.push(`✅ MOMENT filter: ${momentResults.matches?.length || 0} results`);
      debugResult.logs.push(`✅ CONTEXTUAL filter: ${contextualResults.matches?.length || 0} results`);
      
      // Build photo response
      const allPhotos = [
        ...(momentResults.matches?.slice(0, 2).map((match, index) => ({
          photo_id: match.id,
          thumbnail_url: match.metadata?.wordpress_thumbnail,
          modal_url: match.metadata?.wordpress_url || match.metadata?.wordpress_thumbnail,
          caption_moment: match.metadata?.caption_text,
          relevance_score: match.score,
          caption_type: 'MOMENT',
          position: index
        })) || []),
        ...(contextualResults.matches?.slice(0, 2).map((match, index) => ({
          photo_id: match.id,
          thumbnail_url: match.metadata?.wordpress_thumbnail,
          modal_url: match.metadata?.wordpress_url || match.metadata?.wordpress_thumbnail,
          caption_moment: match.metadata?.caption_text,
          relevance_score: match.score,
          caption_type: 'CONTEXTUAL',
          position: index + 2
        })) || [])
      ];
      
      debugResult.step = 'complete';
      debugResult.photos_found = allPhotos.length;
      debugResult.sample_photos = allPhotos.map(p => ({
        id: p.photo_id,
        type: p.caption_type,
        caption: p.caption_moment?.substring(0, 50) + '...',
        has_thumbnail: !!p.thumbnail_url,
        has_modal: !!p.modal_url
      }));
      
      debugResult.logs.push(`✅ Successfully built ${allPhotos.length} photo objects`);

    } catch (error) {
      debugResult.errors.push(`Filter test failed: ${error.message}`);
      return res.status(500).json(debugResult);
    }

    return res.status(200).json(debugResult);

  } catch (error) {
    return res.status(500).json({
      step: 'unknown_error',
      error: error.message,
      stack: error.stack
    });
  }
}
