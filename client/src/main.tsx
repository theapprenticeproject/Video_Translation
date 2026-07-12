import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/react'
import './index.css'
import App from './App.tsx'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string

if (!PUBLISHABLE_KEY) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY in environment')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClerkProvider
      publishableKey={PUBLISHABLE_KEY}
      appearance={{
        variables: {
          // colorPrimary is the same amber in both light and dark modes
          colorPrimary: '#E8A33D',
          borderRadius: '3px',
          fontFamily: 'Inter, system-ui, sans-serif',
          fontFamilyButtons: 'Inter, system-ui, sans-serif',
          // Do NOT hardcode colorBackground/colorForeground here —
          // those are handled by CSS custom properties in index.css
          // which correctly switch via @media (prefers-color-scheme: light/dark).
        },
        elements: {
          card: 'clerk-modal-card',
          formButtonPrimary: 'btn btn--primary',
          footerAction: 'clerk-footer-action',
        },
      }}
    >
      <App />
    </ClerkProvider>
  </StrictMode>,
)
