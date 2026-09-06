import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Rifqy — Networks & Security',
  description: 'Rifqy’s networking, security, CTF, and CCNA work.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
