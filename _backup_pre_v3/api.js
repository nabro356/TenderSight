import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const uploadTender = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/tenders/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const evaluateBidder = async (tenderId, bidderName, files) => {
  const formData = new FormData();
  
  // Append multiple files to the same 'files' key
  files.forEach(file => {
    formData.append('files', file);
  });
  
  const response = await api.post(`/evaluate/${tenderId}/${bidderName}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

/**
 * Evaluate ALL bidders concurrently in a single request.
 *
 * The backend splits files by bidder using the name + count arrays,
 * evaluates them in parallel via a ThreadPoolExecutor, and then runs
 * anomaly + cartel detection on the full set before returning.
 *
 * @param {string} tenderId
 * @param {Array<{name: string, contents: Array}>} bidders
 * @returns {Promise<{evaluations, cartel_alerts}>}
 */
export const evaluateAllBidders = async (tenderId, bidders) => {
  const formData = new FormData();

  // Flatten all bidder files into a single list, tracking counts per bidder
  for (const bidder of bidders) {
    formData.append('bidder_names', bidder.name);

    let fileCount = 0;
    for (const content of bidder.contents) {
      let file;
      if (content.type === 'paste') {
        const blob = new Blob([content.data], { type: 'text/plain' });
        file = new File([blob], `${bidder.name}_text_${fileCount + 1}.txt`, { type: 'text/plain' });
      } else {
        file = content.data;
      }
      formData.append('files', file);
      fileCount++;
    }
    formData.append('bidder_file_counts', fileCount);
  }

  const response = await api.post(`/evaluate_all/${tenderId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    // Allow longer timeout for bulk evaluation (5 minutes)
    timeout: 300000,
  });
  return response.data;
};

/**
 * Connect to the SSE stream for live evaluation progress.
 *
 * @param {string} tenderId
 * @param {function} onBidderComplete - Called with {bidder, status} when a bidder finishes
 * @returns {EventSource} - Close this when done
 */
export const connectEvalStream = (tenderId, onBidderComplete) => {
  const url = `${API_BASE_URL}/evaluate_stream/${tenderId}`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'bidder_complete' && onBidderComplete) {
        onBidderComplete(data);
      }
    } catch (e) {
      console.warn('SSE parse error:', e);
    }
  };

  eventSource.onerror = () => {
    console.warn('SSE connection error, closing.');
    eventSource.close();
  };

  return eventSource;
};

export const updateEvaluation = async (tenderId, bidderName, updatedEvaluation) => {
  const response = await api.post(`/update_evaluation/${tenderId}/${bidderName}`, updatedEvaluation);
  return response.data;
};

export const detectAnomalies = async (tenderId) => {
  const response = await api.post(`/detect_anomalies/${tenderId}`);
  return response.data;
};

export const detectCartels = async (tenderId) => {
  const response = await api.post(`/detect_cartels/${tenderId}`);
  return response.data;
};

export const chatAboutReport = async (tenderId, question) => {
  const response = await api.post('/chat', {
    tender_id: tenderId,
    question,
  });
  return response.data;
};

export const downloadReportPdf = async (tenderId) => {
  const response = await api.get(`/report/${tenderId}`, {
    responseType: 'blob', // Important for downloading files
  });
  return response.data;
};
