import { Pinecone } from '@pinecone-database/pinecone';
import fetch from 'node-fetch'; // Ensure node-fetch is in your package.json

// Helper function to get embeddings via DIRECT REST API CALL
async function getEmbeddingViaRest(text, apiKey) {
  console.log("Attempting to get embedding via REST API for text:", text ? `"${text.substring(0, 50)}..."` : "EMPTY TEXT");
  const url = 'https://api.pinecone.io/embed';
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Api-Key': apiKey,
    'x-pinecone-api-version': '2025-04' // Compatible with SDK v6 features
  };
  const body = JSON.stringify({
    model: 'llama-text-embed-v2',
    inputs: [{ text: text }], // Correctly send as an object within an array
    parameters: {
      input_type: 'query',
      dimension: 1024
    }
  });

  console.log("Calling Pinecone REST API /embed with body:", body);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: headers,
      body: body
    });

    // Try to parse JSON regardless of status for more detailed error logging
    const responseData = await response.json(); 

    if (!response.ok) {
      console.error('Pinecone REST API Error - Status:', response.status);
      console.error('Pinecone REST API Error - Response Body:', JSON.stringify(responseData, null, 2));
      // Construct a more informative error message
      let errorMessage = `API request failed with status ${response.status}.`;
      if (responseData && responseData.message) {
        errorMessage += ` Message: ${responseData.message}`;
      } else if (responseData && responseData.error && responseData.error.message) {
        errorMessage += ` Message: ${responseData.error.message}`;
      } else {
        errorMessage += ` Details: ${JSON.stringify(responseData)}`;
      }
      throw new Error(errorMessage);
    }

    console.log("Raw embedding response from Pinecone REST API:", JSON.stringify(responseData, null, 2));

    if (responseData.data && responseData.data.length > 0 && responseData.data[0].values) {
      console.log("Embedding successfully generated and extracted via REST API.");
      return responseData.data[0].values;
    } else {
      console.error("Unexpected response structure from REST API:", responseData);
      throw new Error('Failed to extract embedding from REST API response. Check logs.');
    }
  } catch (error) {
    console.error('Error calling Pinecone REST API:', error.message);
    if (error.stack) {
        console.error("REST API call error stack:", error.stack);
    }
    // Re-throw a consolidated error message
    throw new Error(`Embedding generation via REST API failed: ${error.message}`);
  }
}

export default async function handler(req, res) {
  console.log("--- Handler Start ---");

  // Standard CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*'); // Adjust in production
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    console.log("Method not allowed:", req.method);
    return res.status(405).json({ error: 'Method not allowed' });
  }

  let queryVector; // To hold the embedding vector

  try {
    const { query, limit = 5 } = req.body;

    if (!query) {
      console.error("Query is missing from request body.");
      return res.status(400).json({ error: 'Query is required in the request body.' });
    }
    console.log("Received query:", query, "Limit:", limit);

    if (!process.env.PINECONE_API_KEY) {
      console.error("CRITICAL: PINECONE_API_KEY environment variable is not set.");
      // Do not expose the exact error message about API key to the client for security
      return res.status(500).json({ error: 'Server configuration error.' });
    }
    const pineconeApiKey = process.env.PINECONE_API_KEY;
    
    console.log("Calling getEmbeddingViaRest function for query:", query);
    // *** USE THE REST API EMBEDDING FUNCTION ***
    queryVector = await getEmbeddingViaRest(query, pineconeApiKey); 

    if (!queryVector || queryVector.length === 0) {
      console.error("Error: getEmbeddingViaRest returned an empty or invalid vector.");
      // This error is specific enough to return if it happens
      return res.status(500).json({ error: 'Failed to generate a valid query embedding. Vector was empty or invalid.' });
    }
    console.log(`Embedding generated via REST. Vector dimension: ${queryVector.length}`);

    // Initialize Pinecone client for querying the index
    // This is done after successful embedding generation
    console.log("Initializing Pinecone client for index query...");
    const pinecone = new Pinecone({ apiKey: pineconeApiKey });
    console.log("Pinecone client initialized for index query.");

    const indexName = 'adas-memory-qa-poc';
    console.log(`Accessing Pinecone index: "${indexName}"`);
    const index = pinecone.index(indexName); // This does not make an API call yet
    console.log("Index object reference obtained.");

    console.log("Querying index with the generated vector...");
    const searchResponse = await index.query({
      vector: queryVector,
      topK: parseInt(limit, 10), // Ensure limit is an integer
      includeMetadata: true
    });
    
    console.log("Raw searchResponse from Pinecone index.query:", JSON.stringify(searchResponse, null, 2));

    if (!searchResponse || typeof searchResponse !== 'object') {
      console.error("Error: searchResponse is undefined or not an object from index.query.");
      throw new Error("Invalid response structure from Pinecone query (searchResponse is falsy or not an object).");
    }
    
    // It's possible to get a valid response object with no matches, or an empty matches array
    const matches = searchResponse.matches || [];
    
    console.log(`Found ${matches.length} matches. Processing...`);
    const results = matches.map(match => {
      const metadata = match.metadata || {}; // Ensure metadata exists
      return {
        question_id: metadata.question_id,
        question_text: metadata.question_text,
        category: metadata.category,
        score: match.score,
        answers: metadata.answers // Assume answers structure is correct or handle further if needed
      };
    });
   
    const SIMILARITY_THRESHOLD = 0.6; // Define your threshold
    if (results.length === 0 || (results[0] && results[0].score < SIMILARITY_THRESHOLD)) {
      console.log("No similar questions found or score below threshold.");
      return res.status(200).json({
        results: [],
        message: "No similar questions found. Try rephrasing your question or click one of the example questions.",
        lowScore: true
      });
    }
 
    console.log("Successfully processed search results.");
    return res.status(200).json({ results });
    
  } catch (error) {
    console.error('API Error in handler:', error.message);
    if (error.stack) {
        console.error("API Error stack:", error.stack);
    }
    // Send a generic error to the client unless it's a specific, safe message
    let clientErrorMessage = 'Internal server error.';
    if (error.message.startsWith("Embedding generation via REST API failed") || 
        error.message.startsWith("Failed to generate a valid query embedding")) {
        clientErrorMessage = error.message; // These are more specific about the embedding step
    }
    return res.status(500).json({ error: clientErrorMessage });
  }
}
