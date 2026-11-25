/* ============================================================
   A.F.O. Oruro · Identidad visual institucional
   Paleta oficial de cuatro familias tomada de la referencia:
      1) Primary    #1D428A
      2) Secondary  #75D1F0
      3) Tertiary   #0F2654
      4) Neutral    #64748B
   Los tonos intermedios son la escala tonal de cada familia
   (tintes y sombras), no colores de acento ajenos a la paleta.
   Tipografía única: Manrope.
   ============================================================ */
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        /* --- Las cuatro familias institucionales --- */
        primary: "#1D428A",
        secondary: "#75D1F0",
        tertiary: "#0F2654",

        /* --- Escala tonal Primary --- */
        "primary-50": "#EEF3FB",
        "primary-100": "#D9E4F7",
        "primary-200": "#B7CDF1",
        "primary-300": "#8FAEE6",
        "primary-400": "#5F84D2",
        "primary-500": "#2F5BB4",
        "primary-600": "#1D428A",
        "primary-700": "#18366F",
        "primary-800": "#132B58",
        "primary-900": "#0F2347",
        "primary-950": "#08152D",

        /* --- Escala tonal Secondary --- */
        "secondary-50": "#EFFBFE",
        "secondary-100": "#DDF6FD",
        "secondary-200": "#BCEDFA",
        "secondary-300": "#9FE0F6",
        "secondary-400": "#75D1F0",
        "secondary-500": "#3FB9DE",
        "secondary-600": "#1E97BE",
        "secondary-700": "#147A9C",
        "secondary-800": "#0F617D",
        "secondary-900": "#0B4B61",
        "secondary-950": "#06303F",

        /* --- Escala tonal Tertiary --- */
        "tertiary-50": "#EEF1F8",
        "tertiary-100": "#DCE3F0",
        "tertiary-200": "#B9C7DE",
        "tertiary-300": "#93A6C9",
        "tertiary-400": "#6B82AE",
        "tertiary-500": "#465E8C",
        "tertiary-600": "#2A4170",
        "tertiary-700": "#1B2F5C",
        "tertiary-800": "#0F2654",
        "tertiary-900": "#0A1B3D",
        "tertiary-950": "#050F24",

        /* --- Escala tonal Neutral --- */
        "neutral-50": "#F4F6F9",
        "neutral-100": "#E8EDF3",
        "neutral-200": "#D5DCE5",
        "neutral-300": "#B6C2D1",
        "neutral-400": "#94A3B8",
        "neutral-500": "#64748B",
        "neutral-600": "#4E5D73",
        "neutral-700": "#3D4A5C",
        "neutral-800": "#2C3646",
        "neutral-900": "#1E2735",
        "neutral-950": "#111827",

        /* --- Derivados semánticos (tinte/sombra de la paleta) --- */
        "primary-container": "#0F2654",
        "primary-fixed": "#D9E4F7",
        "primary-fixed-dim": "#B7CDF1",
        "on-primary": "#FFFFFF",
        "on-primary-container": "#FFFFFF",
        "on-primary-fixed": "#0F2654",
        "on-primary-fixed-variant": "#1D428A",
        "inverse-primary": "#9FE0F6",

        "secondary-container": "#DDF6FD",
        "secondary-fixed": "#EFFBFE",
        "secondary-fixed-dim": "#9FE0F6",
        "on-secondary": "#0F2654",
        "on-secondary-container": "#0F2654",
        "on-secondary-fixed": "#0F2654",
        "on-secondary-fixed-variant": "#1D428A",

        "tertiary-container": "#E8EEF9",
        "tertiary-fixed": "#E8EEF9",
        "tertiary-fixed-dim": "#B9C7DE",
        "on-tertiary": "#FFFFFF",
        "on-tertiary-container": "#1D428A",
        "on-tertiary-fixed": "#0F2654",
        "on-tertiary-fixed-variant": "#1D428A",

        /* --- Superficies: neutro frío con tintes de la paleta --- */
        background: "#F4F6F9",
        "on-background": "#0F2654",
        surface: "#F4F6F9",
        "surface-bright": "#FFFFFF",
        "surface-dim": "#D5DCE5",
        "surface-variant": "#E8EDF3",
        "surface-tint": "#75D1F0",
        "surface-container-lowest": "#FFFFFF",
        "surface-container-low": "#F9FAFC",
        "surface-container": "#EAEFF6",
        "surface-container-high": "#DFE5EE",
        "surface-container-highest": "#D3DBE8",
        "on-surface": "#0F2654",
        "on-surface-variant": "#64748B",
        "inverse-surface": "#0F2654",
        "inverse-on-surface": "#F4F6F9",

        /* --- Bordes --- */
        outline: "#94A3B8",
        "outline-variant": "#D5DCE5",

        /* --- Estados: dentro de la misma paleta ---
           El estado de error usa el tono terciario profundo para
           diferenciarse de las acciones primarias sin salir de la
           paleta institucional. */
        error: "#0F2654",
        "on-error": "#FFFFFF",
        "error-container": "#DCE3F0",
        "on-error-container": "#0F2654",
      },
      fontFamily: {
        sans: ["Manrope", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["Manrope", "system-ui", "sans-serif"],
        "display-lg": ["Manrope", "system-ui", "sans-serif"],
        "headline-lg": ["Manrope", "system-ui", "sans-serif"],
        "headline-lg-mobile": ["Manrope", "system-ui", "sans-serif"],
        "headline-md": ["Manrope", "system-ui", "sans-serif"],
        "headline-sm": ["Manrope", "system-ui", "sans-serif"],
        "title-lg": ["Manrope", "system-ui", "sans-serif"],
        "title-md": ["Manrope", "system-ui", "sans-serif"],
        "body-lg": ["Manrope", "system-ui", "sans-serif"],
        "body-md": ["Manrope", "system-ui", "sans-serif"],
        "body-sm": ["Manrope", "system-ui", "sans-serif"],
        "label-lg": ["Manrope", "system-ui", "sans-serif"],
        "label-md": ["Manrope", "system-ui", "sans-serif"],
        "label-sm": ["Manrope", "system-ui", "sans-serif"],
      },
      fontSize: {
        /* Escala base ampliada para toda la consola */
        xs: ["0.8125rem", { lineHeight: "1.4" }],
        sm: ["0.9375rem", { lineHeight: "1.55" }],
        base: ["1rem", { lineHeight: "1.6" }],
        lg: ["1.125rem", { lineHeight: "1.55" }],
        xl: ["1.3125rem", { lineHeight: "1.4" }],
        "2xl": ["1.625rem", { lineHeight: "1.3" }],
        "3xl": ["2rem", { lineHeight: "1.2" }],
        "4xl": ["2.5rem", { lineHeight: "1.1" }],

        /* Escala semántica del sistema */
        "display-lg": ["3.75rem", { lineHeight: "1.05", letterSpacing: "-0.03em", fontWeight: "800" }],
        "headline-lg": ["2.25rem", { lineHeight: "1.15", letterSpacing: "-0.02em", fontWeight: "800" }],
        "headline-lg-mobile": ["1.75rem", { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "800" }],
        "headline-md": ["1.75rem", { lineHeight: "1.25", letterSpacing: "-0.015em", fontWeight: "800" }],
        "headline-sm": ["1.375rem", { lineHeight: "1.45", letterSpacing: "-0.01em", fontWeight: "700" }],
        "title-lg": ["1.25rem", { lineHeight: "1.6", fontWeight: "700" }],
        "title-md": ["1.0625rem", { lineHeight: "1.5", fontWeight: "700" }],
        "body-lg": ["1.0625rem", { lineHeight: "1.65", fontWeight: "400" }],
        "body-md": ["0.9375rem", { lineHeight: "1.6", fontWeight: "400" }],
        "body-sm": ["0.875rem", { lineHeight: "1.55", fontWeight: "400" }],
        "label-lg": ["0.9375rem", { lineHeight: "1.4", fontWeight: "600" }],
        "label-md": ["0.875rem", { lineHeight: "1.35", letterSpacing: "0.01em", fontWeight: "600" }],
        "label-sm": ["0.75rem", { lineHeight: "1.2", letterSpacing: "0.05em", fontWeight: "700" }],
      },
      borderColor: {
        DEFAULT: "#D5DCE5",
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        sm: "0.375rem",
        md: "0.625rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
        full: "9999px",
      },
      boxShadow: {
        soft: "0 18px 40px -34px rgba(15, 38, 84, 0.45)",
        card: "0 22px 48px -38px rgba(15, 38, 84, 0.50)",
        lift: "0 28px 56px -32px rgba(15, 38, 84, 0.45)",
      },
      spacing: {
        "space-xs": "0.25rem",
        "space-sm": "0.5rem",
        "space-md": "1rem",
        "space-lg": "1.5rem",
        "space-xl": "2rem",
        gutter: "1.5rem",
        "gutter-mobile": "0.75rem",
        margin: "2rem",
        "margin-mobile": "1rem",
      },
    },
  },
};
