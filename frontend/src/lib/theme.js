/**
 * Prep Academy Design System — Theme Tokens & Utilities
 *
 * ── Architecture ──────────────────────────────────────────────
 *
 * 1. CSS Custom Properties are defined in src/index.css
 *    — :root  (light mode)
 *    — .dark  (dark mode)
 *
 * 2. tailwind.config.js maps each CSS variable to a Tailwind color class
 *    e.g., --background → bg-background, text-foreground, border-border
 *
 * 3. shadcn/ui components use cn() to combine Tailwind utility classes
 *    e.g., <div className={cn("rounded-xl border bg-card", className)} />
 *
 * 4. Community / page components use Tailwind classes directly in JSX
 *    These inherit theme tokens through the CSS variable → Tailwind chain.
 *
 * ── How to change colors ────────────────────────────────────
 *
 * Edit only the HSL values in src/index.css under :root and .dark.
 * Do NOT change the variable names — only the triple-hsl values.
 *
 *   --primary: 225 60% 28%;     (hue saturation lightness)
 *
 * To change the primary blue to a different blue:
 *   --primary: 210 80% 30%;   ← new blue
 *
 * To change accent gold to a different accent:
 *   --accent: 160 80% 40%;    ← teal accent
 *
 * ── How to add a completely new theme ────────────────────────
 *
 * 1. Add a new CSS class in index.css that overrides the variables:
 *
 *   .theme-ocean {
 *     --background: 195 40% 97%;
 *     --primary: 195 70% 35%;
 *     --accent: 175 60% 45%;
 *   (... override all other vars ...)
 *   }
 *
 * 2. Apply via Tailwind's class strategy or JS toggle:
 *    document.documentElement.classList.add("theme-ocean");
 *
 * 3. To persist, store preference in localStorage and read in App.js.
 *
 * ── How components inherit styling ───────────────────────────
 *
 *    index.css :root vars  →  tailwind.config.js map  →  Tailwind classes in JSX
 *                                                           ↓
 *                                              cn() + CVA in shadcn components
 *                                                           ↓
 *                                              Page / feature components
 *
 * Components NEVER reference CSS variables directly —
 * they use Tailwind utility classes which resolve through the chain.
 */

/**
 * Spacing rhythm constants (pairs with Tailwind spacing scale)
 * Use these as a reference when adjusting paddings/margins.
 *
 *   px-3 = 0.75rem = 12px  (tight)
 *   px-4 = 1rem    = 16px  (default)
 *   px-5 = 1.25rem = 20px  (spacious)
 *   px-6 = 1.5rem  = 24px  (generous)
 *
 * Border radius tokens:
 *   rounded-lg  = var(--radius)          = 16px
 *   rounded-md  = calc(var(--radius)-2)  = 14px
 *   rounded-sm  = calc(var(--radius)-4)  = 12px
 *   rounded-xl  = 12px (hardcoded in card.jsx — consider unifying)
 *   rounded-2xl = 16px (hardcoded in community components)
 *
 * Shadow tokens (hardcoded in components — consider adding CSS vars):
 *   shadow-sm
 *   shadow-md
 *   shadow-lg
 *   shadow-xl
 *
 * Transition defaults:
 *   transition-colors — for color/border changes
 *   transition-all duration-200 — for hover lifts
 *   transition-transform duration-150 — for scale effects
 */

/**
 * Consistent shadow presets for cards and surfaces.
 * Add as CSS variables if shadows need theming.
 */
export const SHADOWS = {
  card: "shadow-sm hover:shadow-md",
  elevated: "shadow-md hover:shadow-lg",
  modal: "shadow-2xl",
  popover: "shadow-lg",
};

/**
 * Consistent border radius reference.
 */
export const RADII = {
  card: "rounded-xl",
  button: "rounded-lg",
  pill: "rounded-full",
  modal: "rounded-2xl",
};

/**
 * Transition presets for interactive elements.
 */
export const TRANSITIONS = {
  interactive: "transition-[color,background-color,border-color,box-shadow,opacity,transform] duration-200",
  color: "transition-colors duration-150",
  lift: "hover:-translate-y-0.5 hover:shadow-md transition-[transform,box-shadow] duration-200",
  fade: "transition-opacity duration-200",
};
