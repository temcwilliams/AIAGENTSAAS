import type { MetadataRoute } from 'next';
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/', name: 'Agent Meadow', short_name: 'Agent Meadow',
    description: 'Manage your business agents and customer conversations.',
    start_url: '/', scope: '/', display: 'standalone',
    background_color: '#0b1017', theme_color: '#0b1017',
    icons: [
      {src:'/icons/icon-192.png',sizes:'192x192',type:'image/png',purpose:'any'},
      {src:'/icons/icon-512.png',sizes:'512x512',type:'image/png',purpose:'any'},
      {src:'/icons/maskable-512.png',sizes:'512x512',type:'image/png',purpose:'maskable'},
    ],
  };
}
