'use client';

import { useState } from 'react';

interface PdfPreviewProps {
  latex: string;
  apiUrl: string;
}

export default function PdfPreview({ latex, apiUrl }: PdfPreviewProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compilePdf = async () => {
    if (!latex.trim()) {
      setError('No LaTeX content to compile');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/compile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ latex }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Compilation failed');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      // Revoke previous URL if exists
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }

      setPdfUrl(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compile PDF');
    } finally {
      setLoading(false);
    }
  };

  const downloadPdf = () => {
    if (pdfUrl) {
      const link = document.createElement('a');
      link.href = pdfUrl;
      link.download = 'optimized_resume.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div className="card h-full flex flex-col">
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-bluebell">PDF Preview</h2>
          <p className="text-sm text-white/60 mt-1">Compile and preview your resume</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={compilePdf}
            disabled={loading || !latex.trim()}
            className="btn-secondary text-sm"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="spinner w-4 h-4"></span>
                Compiling...
              </span>
            ) : (
              'Compile PDF'
            )}
          </button>
          {pdfUrl && (
            <button
              onClick={downloadPdf}
              className="btn-secondary text-sm bg-bold-green"
            >
              Download
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 p-4 min-h-0">
        {error && (
          <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 mb-4">
            <p className="text-red-300 text-sm font-mono whitespace-pre-wrap">{error}</p>
          </div>
        )}
        {pdfUrl ? (
          <iframe
            src={pdfUrl}
            className="w-full h-full rounded-lg bg-white"
            title="PDF Preview"
          />
        ) : (
          <div className="h-full flex items-center justify-center bg-white/5 rounded-lg border-2 border-dashed border-white/20">
            <div className="text-center text-white/40">
              <svg
                className="w-16 h-16 mx-auto mb-4 opacity-50"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p>Click "Compile PDF" to preview</p>
              <p className="text-sm mt-1">Requires pdflatex installed on the server</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
