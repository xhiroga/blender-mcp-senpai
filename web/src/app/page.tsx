"use client";

import dynamic from 'next/dynamic';

const SimpleChat = dynamic(() => import("@/components/simple-chat").then(mod => ({ default: mod.SimpleChat })), {
  ssr: false,
  loading: () => (
    <div className="flex h-screen bg-white dark:bg-gray-900 items-center justify-center">
      <div className="text-gray-500">Loading...</div>
    </div>
  )
});

export default function Home() {
  return <SimpleChat />;
}
