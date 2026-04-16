# CLAUDE.md - Project Instructions

## Session Start

Before starting any new task, read `TODO.md` (in this directory) to get an up-to-date
picture of outstanding work. Use it to orient quickly without the user needing to
re-explain context. Do not modify `TODO.md` unless the user asks — it is the user's
source of truth for what remains to be done.

## About This Project
This is a learning environment for exploring Claude Code and programming languages.

## Learning Preferences

### Code Comments
- Include detailed comments in all code files (HTML, CSS, JavaScript, Python, etc.)
- Explain what each section does and why it's structured that way
- Use comments to teach programming concepts as they appear in the code

### Explanations
- Provide extensive explanations for all actions taken
- Explain the "why" behind decisions, not just the "what"
- Break down complex concepts into understandable pieces
- Define technical terms when first introduced

## Accessibility Standards

When working on accessibility features, always reference:

### WCAG 2.1 AA Guidelines
- Cite specific success criteria (e.g., WCAG 2.1 SC 1.4.3 for color contrast)
- Explain how implementations meet the criteria
- Link requirements to practical code examples

### Title II of the ADA
- Reference relevant Title II requirements for digital accessibility
- Note that Title II applies to state and local government entities
- Connect technical implementations to legal compliance obligations

## Example Comment Style

```html
<!--
  Navigation Section
  Purpose: Provides site-wide navigation links
  Accessibility: Uses <nav> landmark for screen readers (WCAG 2.1 SC 1.3.1)
  Title II: Ensures equal access to navigation for users with disabilities
-->
<nav aria-label="Main navigation">
  <!-- Navigation content here -->
</nav>
```

```javascript
// Function: calculateTotal
// Purpose: Adds up all items in the shopping cart
// Parameters:
//   - items (array): List of item objects with 'price' property
// Returns: Number representing the total price
function calculateTotal(items) {
  // Use reduce to sum all prices - this iterates through each item
  // and accumulates the total
  return items.reduce((total, item) => total + item.price, 0);
}
```
