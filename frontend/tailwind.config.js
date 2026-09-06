/**
 * Complyx design tokens.
 *
 * Every value here comes from DESIGN.md and carries a reason. Two constraints
 * are absolute and enforced by convention rather than by the compiler, so they
 * are restated where a developer will read them:
 *
 *   1. `redpen` is for findings only. Not delete buttons, not required-field
 *      marks, not network error toasts. When an inspector sees red on this
 *      screen it means the system found a discrepancy in the documents.
 *      Diluting that is the fastest way to make the tool ignorable.
 *
 *   2. No gradients anywhere. Flat ink on flat paper.
 *
 * There is deliberately no dark theme. Inspectors work against scanned white
 * documents all day, and dark chrome around a white scan creates a hard
 * luminance edge at every document boundary -- the exact condition that causes
 * eye strain over an eight-hour review. A paper-toned interface holding a paper
 * document reads as one surface.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    // Replaced, not extended: the default Tailwind palette is 250 colours of
    // temptation. These nine are the whole vocabulary.
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      white: '#FFFFFF',

      /** Application background. Warm paper, not grey. */
      paper: '#F7F5F0',
      /** Document canvas, tables, panels. */
      surface: '#FFFFFF',
      /** Hairlines and grid marks. Borders carry the structure here. */
      rule: '#DDD8CE',
      /** A heavier rule for table heads and structural divisions. */
      'rule-strong': '#C4BDB0',
      /** Primary text. */
      ink: '#1A1A18',
      /** Secondary text, metadata, labels. */
      graphite: '#6B6A65',
      /** Structural accent: active nav, links, extraction outlines. */
      blueprint: '#1B4D7A',
      /** Wash behind blueprint elements. */
      'blueprint-soft': '#E8EFF5',
      /** FINDINGS ONLY. See note above. */
      redpen: '#C1392B',
      'redpen-soft': '#FBEAE8',
      /** Confirmed, verified, cleared. */
      stamp: '#2D6A4F',
      'stamp-soft': '#E6F0EA',
      /** Review required, uncertain, unverified rule. */
      pencil: '#B8860B',
      'pencil-soft': '#FAF0DA',
    },

    // Compressed scale. This is a working instrument; an inspector reviewing
    // forty packages wants density, not air. No 48px headlines.
    fontSize: {
      '2xs': ['11px', { lineHeight: '15px' }],
      xs: ['12px', { lineHeight: '17px' }],
      sm: ['13px', { lineHeight: '19px' }],
      base: ['15px', { lineHeight: '23px' }],
      lg: ['20px', { lineHeight: '26px' }],
      xl: ['28px', { lineHeight: '32px' }],
    },

    fontFamily: {
      // Screen titles and section heads.
      cond: ['"IBM Plex Sans Condensed"', 'Arial Narrow', 'system-ui', 'sans-serif'],
      // Body and prose.
      sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'sans-serif'],
      // Every value, ID, code, date and measurement. The monospace rule is
      // absolute: it makes character-level differences visible, and
      // TPL/GHAVP/W-71 versus TPL/GHAVP/W-72 is exactly the kind of difference
      // this product exists to catch.
      mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
    },

    borderRadius: {
      none: '0',
      DEFAULT: '2px',
      sm: '1px',
    },

    // One level, and only on genuinely floating layers: modals, dropdowns.
    // Never on cards or panels -- borders do that work.
    boxShadow: {
      none: 'none',
      float: '0 1px 2px rgba(26,26,24,0.06)',
      panel: '0 1px 2px rgba(26,26,24,0.06), 0 8px 24px -16px rgba(26,26,24,0.25)',
    },

    extend: {
      // The palette above replaces Tailwind's default, which also removes the
      // default border colour. Without this, a bare `border` falls back to
      // currentColor and renders a hairline in the text colour -- so a red
      // finding value would silently draw a red box around its own container.
      borderColor: { DEFAULT: '#DDD8CE' },
      divideColor: { DEFAULT: '#DDD8CE' },
      letterSpacing: {
        label: '0.06em',
        block: '0.1em',
      },
      borderWidth: {
        3: '3px',
      },
      transitionDuration: {
        120: '120ms',
        200: '200ms',
      },
    },
  },
  plugins: [],
};
