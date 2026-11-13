import type { Metadata, Viewport } from 'next';
import './globals.css';
import Pwa from '../components/pwa';
export const metadata: Metadata = {
  title:'Agent Studio',description:'Your business, powered by intelligent agents',
  applicationName:'Agent Studio', manifest:'/manifest.webmanifest',
  appleWebApp:{capable:true,statusBarStyle:'black-translucent',title:'Agent Studio'},
  icons:{icon:'/icons/icon-192.png',apple:'/icons/apple-touch-icon.png'},
};
export const viewport: Viewport = {themeColor:'#0b1017',width:'device-width',initialScale:1};
export default function Layout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}<Pwa/></body></html>}
