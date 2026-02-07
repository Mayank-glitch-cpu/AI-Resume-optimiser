'use client';

interface JobDescInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function JobDescInput({ value, onChange, disabled }: JobDescInputProps) {
  return (
    <div className="card h-full flex flex-col">
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-old-makeup">Job Description</h2>
        <p className="text-sm text-white/60 mt-1">Paste the target job description</p>
      </div>
      <div className="flex-1 p-4">
        <textarea
          className="input-field h-full resize-none"
          placeholder="Paste the job description here...

Include:
• Job title and company
• Required qualifications
• Preferred skills
• Key responsibilities
• Any specific technologies mentioned"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      </div>
    </div>
  );
}
