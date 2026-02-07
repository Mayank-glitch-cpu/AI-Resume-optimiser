'use client';

import dynamic from 'next/dynamic';

const Editor = dynamic(
  () => import('@monaco-editor/react'),
  { ssr: false }
);

interface ResumeInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function ResumeInput({ value, onChange, disabled }: ResumeInputProps) {
  return (
    <div className="card h-full flex flex-col">
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-old-makeup">LaTeX Resume</h2>
        <p className="text-sm text-white/60 mt-1">Paste your LaTeX resume code below</p>
      </div>
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          defaultLanguage="latex"
          theme="vs-dark"
          value={value}
          onChange={(val) => onChange(val || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            readOnly: disabled,
            padding: { top: 16 },
          }}
        />
      </div>
    </div>
  );
}
