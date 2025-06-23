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

function parseSourceArray(sourceString) {
  if (!sourceString) return [];
  
  try {
    // If it's already an array, return it
    if (Array.isArray(sourceString)) return sourceString;
    
    // If it's a string that looks like an array, parse it
    if (typeof sourceString === 'string' && sourceString.startsWith('[')) {
      return JSON.parse(sourceString);
    }
    
    // If it's a simple string, return as single item array
    return [sourceString];
  } catch (error) {
    console.log('Error parsing source array:', sourceString, error);
    return [sourceString]; // Fallback to treating as single item
  }
}

async function getRelatedPhotos(answerText, answerId, apiKey) {
  try {
    console.log(`=== PHOTO SEARCH START ===`);
    console.log(`Answer text: ${answerText.substring(0, 50)}...`);
    
    // Get embedding using the same REST API workaround as main query
    const answerEmbedding = await getEmbeddingViaRest(answerText, apiKey);
    console.log(`✅ Got embedding, dimension: ${answerEmbedding.length}`);
    
    const fetch = (await import('node-fetch')).default;
    // Updated indexHost to reflect the new production index name.
    // The unique ID (rimyov4) and domain part might change and needs to be verified from the Pinecone console for the 'adas-memory-qa-prod' index.
    // For now, replacing the index name part of the string.
    // const indexHost = 'https://adas-memory-qa-prod-rimyov4.svc.aped-4627-b74a.pinecone.io'; // POC indexHost
    const indexHost = 'https://adas-memory-qa-prod-rimyov4.svc.aped-4627-b74a.pinecone.io'; // Production indexHost
    
    // Search for MOMENT photos using REST API
    console.log(`🔍 Searching for MOMENT photos using REST API...`);
    const momentResponse = await fetch(`${indexHost}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Api-Key': apiKey
      },
      body: JSON.stringify({
        namespace: 'photo-captions',
        vector: answerEmbedding,
        topK: 10, // Get more to ensure we have enough after filtering
        includeMetadata: true,
        filter: {
          prompt_type: { $eq: 'MOMENT' }
        }
      })
    });
    
    // Search for CONTEXTUAL photos using REST API
    console.log(`🔍 Searching for CONTEXTUAL photos using REST API...`);
    const contextualResponse = await fetch(`${indexHost}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Api-Key': apiKey
      },
      body: JSON.stringify({
        namespace: 'photo-captions',
        vector: answerEmbedding,
        topK: 10, // Get more to ensure we have enough after filtering
        includeMetadata: true,
        filter: {
          prompt_type: { $eq: 'CONTEXTUAL' }
        }
      })
    });
    
    if (!momentResponse.ok) {
      throw new Error(`MOMENT photo query failed: ${momentResponse.status}`);
    }
    
    if (!contextualResponse.ok) {
      throw new Error(`CONTEXTUAL photo query failed: ${contextualResponse.status}`);
    }
    
    const momentResults = await momentResponse.json();
    const contextualResults = await contextualResponse.json();
    
    console.log(`📊 MOMENT results: ${momentResults.matches?.length || 0}`);
    console.log(`📊 CONTEXTUAL results: ${contextualResults.matches?.length || 0}`);
    
    // Process MOMENT photos (take top 2)
    const momentPhotos = (momentResults.matches || [])
      .slice(0, 2)
      .map((match, index) => ({
        photo_id: match.id,
        thumbnail_url: match.metadata?.wordpress_thumbnail,
        modal_url: match.metadata?.wordpress_url || match.metadata?.wordpress_thumbnail,
        caption_moment: match.metadata?.caption_text,
        relevance_score: match.score,
        caption_type: 'MOMENT',
        position: index
      }));
    
    // Process CONTEXTUAL photos (take top 2)
    const contextualPhotos = (contextualResults.matches || [])
      .slice(0, 2)
      .map((match, index) => ({
        photo_id: match.id,
        thumbnail_url: match.metadata?.wordpress_thumbnail,
        modal_url: match.metadata?.wordpress_url || match.metadata?.wordpress_thumbnail,
        caption_moment: match.metadata?.caption_text,
        relevance_score: match.score,
        caption_type: 'CONTEXTUAL',
        position: index + 2
      }));
    
    console.log(`📊 Found ${momentPhotos.length} MOMENT photos, ${contextualPhotos.length} CONTEXTUAL photos`);
    
    const allPhotos = [...momentPhotos, ...contextualPhotos];
    
    // If we don't have exactly 4 photos, let's see why
    if (allPhotos.length < 4) {
      console.log(`⚠️  Only found ${allPhotos.length} photos instead of 4`);
      console.log(`   MOMENT: ${momentPhotos.length}, CONTEXTUAL: ${contextualPhotos.length}`);
    }
    
    console.log(`✅ Final result: ${allPhotos.length} photos (${momentPhotos.length} MOMENT, ${contextualPhotos.length} CONTEXTUAL)`);
    
    // Log sample photo for debugging
    if (allPhotos.length > 0) {
      console.log(`Sample photo:`, {
        id: allPhotos[0].photo_id,
        type: allPhotos[0].caption_type,
        has_thumbnail: !!allPhotos[0].thumbnail_url,
        caption: allPhotos[0].caption_moment?.substring(0, 30)
      });
    }
    
    console.log(`=== PHOTO SEARCH END ===`);
    return allPhotos;
    
  } catch (error) {
    console.error(`❌ PHOTO SEARCH ERROR:`, error.message);
    console.error(`❌ Stack:`, error.stack);
    return [];
  }
}

export default async function handler(req, res) {
  console.log("--- Ada's Spark Search Handler ---");

  // CORS Headers - Updated to include Vercel preview URLs
const allowedOrigins = [
  'https://adas-spark.org',
  'https://www.adas-spark.org',
  'http://localhost:8000',
  'http://localhost:3000'
];

const origin = req.headers.origin;

// Check if origin matches allowed patterns
const isAllowed = allowedOrigins.includes(origin) || 
  (origin && origin.includes('joel-swensons-projects.vercel.app')); // Allow all your Vercel previews

if (isAllowed) {
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
    const index = pinecone.index('adas-memory-qa-prod'); // Updated index name
    
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
        // Each match from Pinecone  represents a question.
        // Metadata contains: question_text, category, and answers_json.
        
        let processedAnswers = [];
        if (metadata.answers_json) {
          try {
            const answersFromMetadata = JSON.parse(metadata.answers_json);
            
            for (const answer of answersFromMetadata) {
              // Parse the source arrays
              const sourceTitles = parseSourceArray(answer.source_title);
              const sourceUrls = parseSourceArray(answer.source_url);
              const sourceDates = parseSourceArray(answer.source_date);
              const sourceIds = parseSourceArray(answer.source_post_id);

              //  DEBUG LOGS:
              console.log('DEBUG - Raw source_title:', answer.source_title);
              console.log('DEBUG - Parsed sourceTitles:', sourceTitles);
              console.log('DEBUG - Raw source_url:', answer.source_url);
              console.log('DEBUG - Parsed sourceUrls:', sourceUrls);

              // Create sources array from the parsed data
              const sources = [];
              const maxSources = Math.max(sourceTitles.length, sourceUrls.length, sourceDates.length, sourceIds.length);

              for (let i = 0; i < maxSources; i++) {
                sources.push({
                  id: sourceIds[i] || `source-${i}`,
                  title: sourceTitles[i] || 'CaringBridge Post',
                  url: sourceUrls[i] || '#',
                  date: sourceDates[i] || answer.source_date,
                  type: 'CaringBridge Post'
                });
              }

              processedAnswers.push({
                answer_id: answer.answer_id,
                answer_text: answer.answer_text,
                source_post_id: answer.source_post_id,
                source_date: answer.source_date,
                title: answer.source_title, // Keep for backward compatibility
                url: answer.source_url,     // Keep for backward compatibility
                sources: sources, // Now properly parsed
                related_photos: await getRelatedPhotos(
                  answer.answer_text,
                  answer.answer_id,
                  apiKey
                )
              });
            }
          } catch (error) {
            console.error("Error parsing answers_json for question_id:", match.id, error);
            // Leave processedAnswers as empty if parsing fails
          }
        }
        
        return {
          question_id: match.id, // The ID of the vector is the question_id
          question_text: metadata.question_text,
          category: metadata.category,
          score: match.score, // This is the similarity score for this question
          answers: processedAnswers // Array of all processed answers for this question
        };
      }) || []
    );

    // Check similarity threshold for the top matching question.
    const SIMILARITY_THRESHOLD = 0.5;
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