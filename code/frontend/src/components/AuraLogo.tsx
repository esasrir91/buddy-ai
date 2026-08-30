import React from 'react'

interface Props {
  size?: number
  className?: string
  title?: string
}

/** Official Aura mark — indigo→cyan rounded square with A lettermark */
export default function AuraLogo({ size = 28, className, title = 'Aura' }: Props) {
  return (
    <img
      src="/aura-icon.png"
      width={size}
      height={size}
      alt={title}
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: Math.max(6, Math.round(size * 0.22)),
        display: 'block',
        objectFit: 'cover',
        flexShrink: 0,
        boxShadow: '0 1px 3px rgba(15,23,42,.12)',
      }}
      draggable={false}
    />
  )
}

/** Inline SVG fallback (no network / PNG) — same geometry */
export function AuraLogoSvg({ size = 28, className }: Props) {
  const r = Math.max(6, Math.round(size * 0.22))
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 128 128"
      className={className}
      aria-hidden
      style={{ display: 'block', flexShrink: 0, borderRadius: r }}
    >
      <defs>
        <linearGradient id="auraGrad" x1="16" y1="12" x2="112" y2="116" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4F46E5" />
          <stop offset=".55" stopColor="#2563EB" />
          <stop offset="1" stopColor="#06B6D4" />
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="120" height="120" rx="28" fill="url(#auraGrad)" />
      <path
        d="M64 28 L96 96 H82.5 L75.2 76 H52.8 L45.5 96 H32 L64 28 Z M57.2 64 H70.8 L64 46.5 Z"
        fill="#fff"
        fillRule="evenodd"
      />
    </svg>
  )
}
