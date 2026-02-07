'use client';

import { useState } from 'react';
import ResumeInput from '@/components/ResumeInput';
import JobDescInput from '@/components/JobDescInput';
import ResultView from '@/components/ResultView';
import PdfPreview from '@/components/PdfPreview';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8001';

export default function Home() {
  const [latex, setLatex] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [optimizedLatex, setOptimizedLatex] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleOptimize = async () => {
    if (!latex.trim() || !jobDescription.trim()) {
      setError('Please provide both a LaTeX resume and a job description');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch(`${API_URL}/api/optimize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          latex,
          job_description: jobDescription,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Optimization failed');
      }

      const data = await response.json();

      if (data.success) {
        setOptimizedLatex(data.optimized_latex);
        setSuccess(true);
      } else {
        throw new Error(data.optimization_summary || 'Optimization failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to optimize resume');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-mountain-shadow">
      {/* Header */}
      <header className="border-b border-white/10 bg-mountain-shadow/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-goldenrod to-old-makeup rounded-lg flex items-center justify-center">
              <span className="text-mountain-shadow font-bold text-xl">R</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Resume Optimizer</h1>
              <p className="text-xs text-white/50">Powered by Claude AI</p>
            </div>
          </div>
          <a
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-bluebell hover:text-old-makeup transition-colors"
          >
            API Docs →
          </a>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Input Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6" style={{ height: '50vh' }}>
          <ResumeInput
            value={latex}
            onChange={setLatex}
            disabled={loading}
          />
          <JobDescInput
            value={jobDescription}
            onChange={setJobDescription}
            disabled={loading}
          />
        </div>

        {/* Action Button */}
        <div className="flex flex-col items-center gap-4 mb-6">
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg px-4 py-2 text-red-300 text-sm fade-in">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-bold-green/20 border border-bold-green/50 rounded-lg px-4 py-2 text-bold-green text-sm fade-in pulse-success">
              ✓ Resume optimized successfully!
            </div>
          )}
          <button
            onClick={handleOptimize}
            disabled={loading || !latex.trim() || !jobDescription.trim()}
            className="btn-primary text-lg px-8 py-4"
          >
            {loading ? (
              <span className="flex items-center gap-3">
                <span className="spinner"></span>
                Optimizing with Claude...
              </span>
            ) : (
              '✨ Optimize Resume'
            )}
          </button>
        </div>

        {/* Results Section */}
        {optimizedLatex && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in" style={{ height: '60vh' }}>
            <ResultView
              latex={optimizedLatex}
              onLatexChange={setOptimizedLatex}
            />
            <PdfPreview
              latex={optimizedLatex}
              apiUrl={API_URL}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-8 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-white/40 text-sm">
          <p>Resume Optimizer • Built for JobHunt AI integration</p>
          <p className="mt-1">API available at <code className="text-bluebell">{API_URL}/api</code></p>
        </div>
      </footer>
    </main>
  );
}
