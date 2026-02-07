'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';

const Editor = dynamic(
  () => import('@monaco-editor/react'),
  { ssr: false }
);

interface ResultViewProps {
  latex: string;
  onLatexChange: (value: string) => void;
}

export default function ResultView({ latex, onLatexChange }: ResultViewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(latex);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="card h-full flex flex-col">
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-bold-green">Optimized LaTeX</h2>
          <p className="text-sm text-white/60 mt-1">Review and edit the optimized resume</p>
        </div>
        <button
          onClick={handleCopy}
          className={`btn-secondary text-sm ${copied ? 'bg-bold-green' : ''}`}
        >
          {copied ? '✓ Copied!' : 'Copy LaTeX'}
        </button>
      </div>
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          defaultLanguage="latex"
          theme="vs-dark"
          value={latex}
          onChange={(val) => onLatexChange(val || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 16 },
          }}
        />
      </div>
    </div>
  );
}
