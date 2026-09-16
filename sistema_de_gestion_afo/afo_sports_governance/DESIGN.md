---
name: AFO Sports Governance
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#434651'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#747782'
  outline-variant: '#c4c6d2'
  surface-tint: '#3b5ca5'
  primary: '#002b6d'
  on-primary: '#ffffff'
  primary-container: '#1d428a'
  on-primary-container: '#93b2ff'
  inverse-primary: '#b1c6ff'
  secondary: '#00677f'
  on-secondary: '#ffffff'
  secondary-container: '#82defd'
  on-secondary-container: '#006279'
  tertiary: '#182d5b'
  on-tertiary: '#ffffff'
  tertiary-container: '#304473'
  on-tertiary-container: '#9fb2e9'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d9e2ff'
  primary-fixed-dim: '#b1c6ff'
  on-primary-fixed: '#001946'
  on-primary-fixed-variant: '#1f438b'
  secondary-fixed: '#b6ebff'
  secondary-fixed-dim: '#77d3f2'
  on-secondary-fixed: '#001f28'
  on-secondary-fixed-variant: '#004e60'
  tertiary-fixed: '#dae2ff'
  tertiary-fixed-dim: '#b2c5fd'
  on-tertiary-fixed: '#001946'
  on-tertiary-fixed-variant: '#314575'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 3.5rem
    fontWeight: '700'
    lineHeight: 4rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 2rem
    fontWeight: '700'
    lineHeight: 2.5rem
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 1.5rem
    fontWeight: '700'
    lineHeight: 2rem
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Outfit
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Outfit
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: -0.005em
  title-lg:
    fontFamily: Outfit
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
  title-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '600'
    lineHeight: 1.5rem
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
  label-lg:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.25rem
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '600'
    lineHeight: 1rem
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '700'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 0.75rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes an authoritative, energetic, and impeccably structured digital environment tailored for the administrative and competitive needs of regional association football. It combines the rigor of corporate governance platforms with the dynamism and kinetic clarity of modern sports analytics.

The aesthetic fuses **Corporate/Modern** structural discipline with high-performance sports dashboard paradigms. The UI evokes reliability, administrative transparency, civic pride, and competitive precision. It rejects decorative clutter in favor of crisp borders, high-density data visualizations, legible telemetry, and clear hierarchical signifiers suited for club delegates, tournament directors, referees, and league administrators.

## Colors

The palette is anchored by the deep institutional navy, balanced by energetic athletic cyan accents and clean neutral foundations.

- **Primary (`#1D428A`)**: Deep Institutional Royal Blue. Communicates heritage, regulatory governance, authority, and official identity. Used for primary navigation, critical interactive controls, and authoritative state indicators.
- **Secondary (`#75D1F0`)**: Electric Sky Cyan. Delivers high-contrast visual cadence. Used for key accents, active states, score tickers, progress metrics, and live match day highlights.
- **Tertiary (`#0F2654`)**: Midnight Navy. Used for dense header bars, high-contrast table headers, dark surfaces, and prominent institutional cards.
- **Neutral Surface & Structure**:
  - Main Canvas: `#F4F6F9` (Gris suave de fondo).
  - Surface Containers: `#FFFFFF` (Blanco limpio).
  - Subtle Dividing Lines & Table Borders: `#E2E8F0`.
  - Body Text: `#1E293B` (Slate 800).
  - Secondary Metadata & Inactive Icons: `#64748B` (Slate 500).
- **Functional Semantics**:
  - Success (Sanction cleared, Match verified): `#10B981`.
  - Warning / Caution (Yellow card, Pending roster sanction): `#F59E0B`.
  - Danger (Red card, Suspended player, Expired affiliation): `#EF4444`.

## Typography

The typographic pairing pairs the geometric athleticism of **Outfit** with the neutral, hyper-legible precision of **Inter**.

- **Outfit (Headlines & Institutional Display)**: Infuses scoreboards, league standings, match titles, and module banners with structural character and athletic momentum.
- **Inter (Body, Controls, & Data Densities)**: Designed for mission-critical legibility across dense sports registries, referee match minutes (*planillas de juego*), and financial transfers. Tabular numerals (`font-feature-settings: 'tnum'`) must be enabled on all numerical representations, scores, minute logs, and monetary entries.
- **Case Formatting**: `label-sm` applies uppercase styling by default when employed for status tags, table column categorizations, or tournament tiers (e.g., "PRIMERA A", "SUB-19", "EN JUEGO").

## Layout & Spacing

The layout model is driven by a 12-column fluid grid system optimized for information-dense sports back-office and competition interfaces.

- **Desktop (1200px and up)**: 12-column fluid layout with `margin: 2rem` and `gutter: 1.5rem`. Side navigation panels remain persistent at `260px` fixed width, reserving the remainder for administrative workspaces, double-bracket match views, and dense data tables.
- **Tablet (768px - 1199px)**: 8-column layout with `margin: 1.5rem` and `gutter: 1rem`. Side navigation collapses into an icon rail (`72px`), and complex tables toggle into horizontal scrollers with pinned identification columns (Player Name / Club).
- **Mobile (< 768px)**: 4-column layout with `margin: 1rem` and `gutter: 0.75rem`. Score sheets and fixture cards stack vertically, converting multi-column statistics into expandable summary accordions.
- **Vertical Rhythm**: Spacing scales strictly along multiples of 4px. Element padding inside data components uses compact values (`space-xs` and `space-sm`) to maximize visible information density per viewport.

## Elevation & Depth

This system avoids heavy drop shadows, instead adopting a structural layering approach using **low-contrast outlines** and **crisp surface stacking**.

- **Base Layer**: Background canvas sits at `#F4F6F9`.
- **Card and Table Surface**: Elevated one step via solid `#FFFFFF` fill framed by a crisp `1px solid #E2E8F0` border. Shadows are minimized to flat architectural geometry.
- **Hover & Interaction State**: Interactive cards and table rows apply a subtle tinted shadow: `box-shadow: 0 4px 12px -2px rgba(29, 66, 138, 0.08)`, complemented by a border shift to `#75D1F0`.
- **Modals & Overlays (Match Minutes, Player Dossiers)**: Elevated above backdrop dimmers (`rgba(15, 38, 84, 0.45)`) using a sharp ambient elevation: `box-shadow: 0 20px 25px -5px rgba(15, 38, 84, 0.12), 0 8px 10px -6px rgba(15, 38, 84, 0.08)`.

## Shapes

The design uses **Soft (`roundedness: 1`)** geometry. 

- Core interactive elements (buttons, text inputs, table headers, filter bars) leverage `4px` (`0.25rem`) corner radii, reinforcing institutional rigor and precision.
- Structural cards, panel containers, and dialog frames use `8px` (`0.5rem`).
- Athlete headshot avatars use circular framing (`9999px`), whereas club crests are displayed inside soft-cornered framed badges (`6px`) with neutral inset backgrounds to prevent logo clash.
- Status badges and match timer pills use `4px` radii rather than full pills to retain an architectural, sports-governance look.

## Components

### Buttons
- **Primary**: Solid `#1D428A` fill, white typography, `4px` radius, `height: 40px` (desktop) / `36px` (compact data views). Inset padding: `0.75rem 1.25rem`. Hover state transitions to `#15326A`.
- **Accent / Action**: Solid `#75D1F0` fill with tertiary navy `#0F2654` text for high-impact callouts (e.g., "Aprobar Planilla", "Registrar Gol").
- **Secondary / Outline**: `#FFFFFF` background, `1px solid #E2E8F0`, text `#1D428A`. Hover brings `#F4F6F9` fill and `#1D428A` border.
- **Destructive**: Border or fill using `#EF4444` for red cards, disqualifications, or registration cancellations.

### Data Tables (Tournament Standings, Roster Registrations)
- **Header Row**: `#0F2654` background with `#FFFFFF` text or neutral `#F8FAFC` background with `#475569` uppercase `label-sm` text and `1px solid #E2E8F0` lower border.
- **Rows**: Alternating row color or clean `#FFFFFF` with `1px solid #E2E8F0` separators. Hover color: `rgba(117, 209, 240, 0.06)`. Cell vertical padding: `0.5rem` (dense) to `0.75rem` (default).
- **Numeric Alignment**: Numerical statistics (PTS, PJ, PG, PE, PP, GF, GC, DIF) must be right-aligned with fixed-width tabular numbers.

### Badges & Match State Indicators
- **Live Match**: `#75D1F0` background with `#0F2654` text, featuring a pulse indicator dot.
- **Sanctions**:
  - Yellow Card: `#FEF3C7` background, `#92400E` text, accompanied by a 2:3 vertical yellow card icon.
  - Red Card: `#FEE2E2` background, `#991B1B` text, accompanied by a 2:3 vertical red card icon.
  - Medical / Transfer Clearance: `#ECFDF5` background, `#065F46` text.

### Form Inputs & Selectors
- **Input Fields**: Height `40px`, background `#FFFFFF`, border `1px solid #E2E8F0`, corner radius `4px`.
- **Focus State**: `border-color: #1D428A`, with an electric cyan outer glow: `box-shadow: 0 0 0 3px rgba(117, 209, 240, 0.35)`.
- **Labels**: Positioned above the field in `label-md` weight, colored `#1E293B`.

### Domain-Specific Components
- **Scoreboard Fixture Tile**: Split block displaying home/away clubs, club crests, scheduled kickoff time, stadium tag (e.g., "Estadio Jesús Bermúdez"), and score display using Outfit Bold numbers.
- **Match Sheet Minute Logger (Planilla Arbitral)**: Timeline container recording events per minute (goals, substitutions, bookings) with high-contrast icon badges and designated referee digital signature verification status.