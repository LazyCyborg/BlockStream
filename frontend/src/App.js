import React, { useState, useEffect } from 'react';
import { AlertCircle, Play, Square, Settings, HardDrive, FileAudio, FileText } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5001/api';

function App() {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState({
    isRunning: false,
    currentBlock: null,
    currentLoop: 0,
    audioProcessing: { isProcessing: false, results: null, error: null },
    textAnalysis: { isAnalyzing: false, results: null, error: null }
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchConfig();
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/get-config`);
      const data = await response.json();
      if (data.success) {
        setConfig(data.config);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('Failed to fetch configuration');
    }
  };

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError('Failed to fetch status');
    }
  };

  const handleStart = async () => {
    try {
      // Initialize experiment
      const initResponse = await fetch(`${API_BASE_URL}/initialize`, {
        method: 'POST',
      });
      const initData = await initResponse.json();
      
      if (!initData.success) {
        setError(initData.error);
        return;
      }

      // Start experiment
      const startResponse = await fetch(`${API_BASE_URL}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config })
      });
      const startData = await startResponse.json();
      
      if (!startData.success) {
        setError(startData.error);
      }
    } catch (err) {
      setError('Failed to start experiment');
    }
  };

  const handleStop = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/stop`, {
        method: 'POST'
      });
      const data = await response.json();
      if (!data.success) {
        setError(data.error);
      }
    } catch (err) {
      setError('Failed to stop experiment');
    }
  };

  const handleProcessAudio = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/process-audio`, {
        method: 'POST'
      });
      const data = await response.json();
      if (!data.success) {
        setError(data.error);
      }
    } catch (err) {
      setError('Failed to process audio');
    }
  };

  const handleAnalyzeText = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/analyze-text`, {
        method: 'POST'
      });
      const data = await response.json();
      if (!data.success) {
        setError(data.error);
      }
    } catch (err) {
      setError('Failed to analyze text');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h1 className="text-2xl font-bold mb-4">Experiment Control Panel</h1>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded flex items-center mb-4">
              <AlertCircle className="w-5 h-5 mr-2" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Main Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Experiment Controls</h2>
            <div className="flex space-x-4">
              <button
                onClick={handleStart}
                disabled={status.isRunning}
                className="flex items-center bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:opacity-50"
              >
                <Play className="w-5 h-5 mr-2" />
                Start
              </button>
              <button
                onClick={handleStop}
                disabled={!status.isRunning}
                className="flex items-center bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 disabled:opacity-50"
              >
                <Square className="w-5 h-5 mr-2" />
                Stop
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Status</h2>
            <div className="space-y-2">
              <p>Running: {status.isRunning ? 'Yes' : 'No'}</p>
              <p>Current Loop: {status.currentLoop}</p>
              <p>Current Block: {status.currentBlock?.type || 'None'}</p>
            </div>
          </div>
        </div>

        {/* Processing Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Audio Processing</h2>
            <button
              onClick={handleProcessAudio}
              disabled={status.audioProcessing.isProcessing}
              className="flex items-center bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
            >
              <FileAudio className="w-5 h-5 mr-2" />
              Process Audio
            </button>
            {status.audioProcessing.isProcessing && (
              <p className="mt-2 text-blue-600">Processing audio...</p>
            )}
            {status.audioProcessing.error && (
              <p className="mt-2 text-red-600">{status.audioProcessing.error}</p>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Text Analysis</h2>
            <button
              onClick={handleAnalyzeText}
              disabled={status.textAnalysis.isAnalyzing}
              className="flex items-center bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600 disabled:opacity-50"
            >
              <FileText className="w-5 h-5 mr-2" />
              Analyze Text
            </button>
            {status.textAnalysis.isAnalyzing && (
              <p className="mt-2 text-purple-600">Analyzing text...</p>
            )}
            {status.textAnalysis.error && (
              <p className="mt-2 text-red-600">{status.textAnalysis.error}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;