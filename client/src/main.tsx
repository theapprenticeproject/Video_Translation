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
          colorBackground: '#0E1210',
          colorPrimary: '#E8A33D',
          colorForeground: '#F3EFE6',
          colorMutedForeground: 'rgba(243,239,230,0.45)',
          colorInput: 'transparent',
          colorInputForeground: '#F3EFE6',
          borderRadius: '3px',
          fontFamily: 'Inter, system-ui, sans-serif',
          fontFamilyButtons: 'Inter, system-ui, sans-serif',
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
