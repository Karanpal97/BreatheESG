'use client';
import { Suspense } from 'react';
import RecordsContent from './RecordsContent';

export default function RecordsPage() {
  return (
    <Suspense fallback={<div className="loading-spinner" style={{ minHeight: '100vh' }}><div className="spinner" /></div>}>
      <RecordsContent />
    </Suspense>
  );
}
