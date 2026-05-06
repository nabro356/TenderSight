import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

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
