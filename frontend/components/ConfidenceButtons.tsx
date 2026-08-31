'use client';

interface ConfidenceButtonsProps {
  onSelect: (confidence: 'again' | 'hard' | 'good' | 'easy') => void;
}

export default function ConfidenceButtons({ onSelect }: ConfidenceButtonsProps) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '1rem' }}>
      <button onClick={() => onSelect('again')} style={{ background: '#ef4444', padding: '0.875rem', borderRadius: '8px', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
        Again<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400, opacity: 0.9 }}>1 day interval</span>
      </button>
      <button onClick={() => onSelect('hard')} style={{ background: '#f59e0b', padding: '0.875rem', borderRadius: '8px', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
        Hard<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400, opacity: 0.9 }}>Shorter interval</span>
      </button>
      <button onClick={() => onSelect('good')} style={{ background: '#10b981', padding: '0.875rem', borderRadius: '8px', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
        Good<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400, opacity: 0.9 }}>Normal interval</span>
      </button>
      <button onClick={() => onSelect('easy')} style={{ background: '#3b82f6', padding: '0.875rem', borderRadius: '8px', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
        Easy<span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400, opacity: 0.9 }}>Longer interval</span>
      </button>
    </div>
  );
}
