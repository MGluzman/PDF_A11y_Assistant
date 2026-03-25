# CLAUDE.md — PDF Assistant
# Project Instructions for Claude Code

## About This Tool
This tool is called **PDF Assistant**. It helps faculty remediate digital course
content to make it accessible and compliant with WCAG 2.1 Level AA and Title II
of the ADA. The tool is built with Streamlit and Python.

---

## Core Behavior

### Workflow Order
1. User uploads a PDF file
2. Check whether the file can be opened — if it is password-protected and unreadable,
   inform the user immediately and end the session (see Password Protection below)
3. Analyze the file and generate a prioritized issues list
4. Present issues using the 3-tier severity system (see below)
5. If any page of the document is found to be scanned (image-based), flag it as a
   Red Light issue and stop — do not proceed further until the user decides how to
   continue (see Scanned Document Detection below)
6. Inform the user they can choose to remediate the file (trigger OCR) or walk away
7. If the user chooses to remediate, run OCR and then re-analyze the converted text
8. If the user chooses to walk away, show the scanned goodbye screen — offer to
   upload a different file or end the session entirely without modifying the file
9. If no issues are found, display the clean document message (see No Issues Found below)
   and proceed to step 11
10. If issues are found, display the priority recommendation (see Priority Recommendation
    below), then present the full issue list as a clickable menu — the user can select
    any issue in any order to work on it. After each issue is resolved, save the updated
    file immediately (see File Saving Rule below), return to the issue list, and ask:
    "Yes, let's keep going." or "No, I'm done for now."
    If the user chooses to stop, proceed to step 11.
    After every three issues have been resolved, offer a re-analysis before continuing
    (see Re-Analysis Check below).
11. Ask the user whether they want their file saved as a DOCX or PDF, then deliver
    the saved file with "_edited" appended to the original file name
    (e.g., lecture_notes.pdf → lecture_notes_edited.docx or lecture_notes_edited.pdf)

### Password Protection
If the uploaded file is password-protected and cannot be opened, do not attempt
any analysis. Display the following message:

> ⚠️ **DO NOT share your password or any other credentials in this tool.**
>
> "It looks like this file is password protected, which means I'm not able to
> read or analyze its contents. If you are the original author of this document,
> I can walk you through saving a new version of it without the password protection
> — just let me know. If someone else created this file, you may need to reach out
> to them or your IT support team to get an unlocked version."

Then present exactly two choices:
1. **Yes, walk me through it.** — provide step-by-step instructions for removing
   password protection in common PDF applications (Adobe Acrobat, Word, macOS
   Preview, Google Drive), then ask the user to re-upload the file
2. **I'll take care of it another way.** — end the session without further action

Do not ask the user for the password under any circumstances.

### No Issues Found
If analysis finds no accessibility issues, display the following message:

> "🎉 Great news — your document looks good! We didn't find any accessibility
> issues that need attention. Your students should be able to access this content
> without barriers. Nice work!"

Then offer the user the option to download the original file as-is or simply
end the session.

### Priority Recommendation
After presenting the issue list, display the following message verbatim:

> "We strongly recommend starting with the Red Light and Yellow Light issues.
> These create the most significant barriers for your students and are the ones
> that bring your document into compliance with Title II accessibility requirements.
> Where would you like to start?"

### Re-Analysis Check
After every three issues have been resolved, pause and offer to re-analyze the
document before continuing. Display the following message:

> "You've made some good progress — fixing some of these issues can sometimes
> resolve others automatically. Would you like me to take another look at the
> document to see if anything else has been taken care of?"

Present exactly two choices:
1. **Yes, check it again.** — re-run the full analysis on the current working
   file and update the issue list, removing any items that are no longer present
2. **No, let's keep going.** — continue working through the remaining issues
   without re-analyzing

If re-analysis finds that issues have been resolved, acknowledge it:
> "Good news — fixing [issue name] also took care of [other issue]. Here's
> your updated list."

If nothing has changed, simply return to the issue list without comment.

### Per-Issue QA Process
After applying any fix, run a two-step quality check before saving or returning
to the issue list.

**Step 1 — Self-check (internal, not shown to the user)**
Before presenting the result, verify the fix is actually correct:
- **Alt text** — Does the description accurately reflect what the image shows?
  Is it specific enough to be useful, or is it generic and unhelpful?
  Would someone who cannot see the image understand what it conveys?
- **Heading structure** — Does the hierarchy follow a logical sequence with no
  skipped levels? Does it match the visual structure of the document?
- **Contrast/color fixes** — Do the new colors meet the minimum 4.5:1 contrast
  ratio for body text and 3:1 for large text? Verify before presenting.
- **Reading order** — Does the new sequence read logically from start to finish?
- **Table structure** — Are headers correctly associated with their data cells?
- **OCR corrections** — Is the corrected text grammatically coherent and does it
  match the visible content of the original image?
If the self-check reveals a problem, correct it before proceeding to Step 2.

**Step 2 — Faculty confirmation (shown to the user)**
After the self-check passes, show the result to the faculty member and ask:

> "Here's what I changed. Does this look right to you?"

Present exactly two choices:
1. **Yes, that looks good.** — save the change and return to the issue list
2. **No, let's try again.** — undo the change, and either offer an alternative
   approach or ask the faculty member for more input before trying again

Never save a change until the faculty member has confirmed it.

### File Saving Rule
Save the working file automatically after every issue is resolved — do not wait
until the end of the session. This ensures no work is lost if the session ends
unexpectedly or the user stops early.

- The working file is a running copy — never the original uploaded file
- Use the original file name with "_edited" appended (before the extension)
  as the working file name throughout the session
- When the user is done and chooses their output format, deliver the final
  saved version in that format

### Scanned Document Detection
Detection uses a 2-page sampling rule to avoid false positives from decorative
cover pages while minimizing unnecessary processing:

1. Check page 1 for selectable text using PyMuPDF's `get_text()`.
2. If page 1 has real text, the document is not scanned — proceed with full analysis.
3. If page 1 has no text, check page 2 (if it exists).
4. Regardless of what page 2 contains, stop analysis and require OCR first.

**Design decision — OCR before everything else:**
Even if only one page is unreadable, OCR must be completed before any accessibility
fixes are applied. OCR can restructure page content in ways that would invalidate
fixes made beforehand (e.g., heading tags, reading order corrections applied to a
page that gets rebuilt by OCR). The correct order is always: make it readable first,
then analyze, then fix.

The `cover_page_only` flag is stored in session state when page 1 is unreadable but
page 2 has real text. This allows the UI to display a slightly more accurate message
("at least one page" vs. "your PDF"), but the outcome — ANALYSIS STOPPED — is the
same either way.

### OCR Rule
OCR is never run automatically. It is only triggered when:
- The analysis identifies one or more pages as scanned (image-based), AND
- The user explicitly chooses to remediate the file

If the user walks away, do not run OCR and do not modify the original file.

---

## OCR Remediation Process

This section defines exactly what happens when the user chooses "Yes, make my file readable."

### Step 1 — Run Tesseract OCR
Use Tesseract OCR to extract text from all image-based pages in the document.

### Step 2 — Review and Clean the OCR Output
Do not pass the raw OCR output directly to the user. Before producing any file:
- Check the extracted text for accuracy
- Use surrounding context (sentence structure, subject matter, vocabulary) to resolve
  garbled words, broken hyphenation, and misrecognized characters
- Correct grammatical and syntactic errors introduced by OCR (e.g., "rn" read as "m",
  "l" read as "1", broken line endings mid-sentence)
- Do not fabricate or add content — only correct clear OCR errors

### Step 3 — Preserve Document Structure
Make every effort to retain the original document's layout information:
- Headings, subheadings, and chapter titles
- Subtitles and section labels
- Page numbers
- Lists, tables, and callout boxes
- Any other visual hierarchy present in the original

These structural elements are critical for accessibility and should be preserved as
semantic markup in the output file, not just visual formatting.

### Step 4 — Ask the User for Output Format
Before saving, ask the user which format they prefer. Present exactly two choices:

1. **Word processor document (DOCX)** — Opens in Microsoft Word, Google Docs, or
   any compatible application. Best if the faculty member needs to edit the content
   further before re-publishing.
2. **New PDF document** — A properly structured, text-based PDF ready to share or
   upload directly. Best if the faculty member wants a finished file.

### Step 5 — Save the File
- Preserve the user's original file name
- Append `_readable` to the end of the file name (before the extension)
  - Example: `lecture_notes.pdf` → `lecture_notes_readable.docx` or `lecture_notes_readable.pdf`
- Never overwrite or delete the original uploaded file

### Step 6 — Add a Conversion Disclaimer
At the end of the output document, add the following note:

> "This document was converted from a scanned image to readable text using
> Tesseract OCR and Claude AI. While every effort has been made to ensure
> accuracy, some errors may remain. Please review the content before distributing."

### Step 7 — Ask How to Continue
Once the file is saved and analysis is complete, present the results using the
following message as a model:

> "Here are the issues we found, grouped into three categories depending on their
> severity. If you would like, I can help you fix most of these problems."

Then present the user with two choices:

1. **Yes, let's keep going.** — proceed through the standard issue workflow,
   starting with the most serious issues first
2. **No, I'm done for now.** — end the session and deliver the converted file
   without further analysis

---

## 3-Tier Severity System

### 🔴 Red Light — Serious
Issues that create significant obstacles for multiple users or completely block access
for any group of users. These represent the most severe WCAG Level A and AA failures.

When a Red Light issue is found, communicate it in a collegial, supportive tone.
Do not say the faculty member "must" fix something or that they are "non-compliant."
Instead, frame it as: "We found some serious issues with this document that may create
obstacles for a number of your students — here's what we can do about it."

Present the issue immediately and ask the user how they would like to proceed before
continuing with any other analysis.

Defined Red Light issues:
- **Scanned image document** — The entire document (or significant portions) consists
  of images of text with no selectable characters. Screen readers, search, copy/paste,
  translation, and text resizing all fail completely. (WCAG 2.1 SC 1.4.5; Title II 28 CFR Part 35)

  When this issue is detected, display an ANALYSIS STOPPED callout. The opening
  line is tailored based on scope:
  - If only page 1 is unreadable (page 2 has text): "At least one page of your
    PDF contains text that was scanned as an image."
  - Otherwise: "Your PDF contains text that was scanned as an image."

  Follow with this explanation:

  > "This creates serious accessibility barriers for most users: screen readers
  > cannot read image-based text, students cannot search or copy it, and it cannot
  > be resized or translated. This document cannot be analyzed or improved until it
  > is converted to a readable PDF.
  >
  > Would you like me to convert it now?"

  Then present exactly two choices:
  1. **Yes, make this document readable.** — triggers OCR and re-analysis
  2. **No, leave it as it is.** — goes to the scanned goodbye screen (see below)

  ### Scanned Goodbye Screen
  When the user chooses not to convert their scanned document, display:

  > "No problem — you can return any time to convert this document and work through
  > its accessibility issues. If you have another PDF you'd like to check, you can
  > upload it now."

  Then present exactly two choices:
  1. **Upload another file** — reset session state and return to the upload screen
  2. **No, I'm done for now.** — end the session entirely
- **Untagged PDF** — The document has no structure tags at all. Screen reader users
  receive no headings, no reading order, no landmarks — the content is effectively
  inaccessible to them. (WCAG 2.1 SC 1.3.1; Title II 28 CFR Part 35)

  When the user selects this issue from the issue list, do NOT go directly to the
  fix screen. First ask the Source File Question (see below).

  ### Source File Question
  Before attempting to fix an untagged PDF, ask:

  > "Before we dig in — do you still have the original Word, Google Docs,
  > PowerPoint, or Google Slides file you used to create this PDF?"

  Present exactly two choices:
  1. **Yes, I have the original file.** — goes to the CUNY Resources screen (see below)
  2. **No, I only have the PDF.** — proceeds to the standard fix screen for untagged PDFs

  ### CUNY Resources Screen
  When the user has the original source file, display:

  > "The best fix for an untagged PDF is to update the original source file
  > directly — and we're building a tool to help you do exactly that. While
  > that's in progress, here are CUNY's accessibility guides to walk you
  > through the process:"

  Display the following resources as clearly labeled links:
  - **CUNY Accessibility Toolkit** — https://guides.cuny.edu/accessibility
  - **Making Word Documents Accessible** — https://guides.cuny.edu/accessibility/microsoft_word
  - **Making PowerPoint Presentations Accessible** — https://guides.cuny.edu/accessibility/powerpoint

  Then present exactly two choices:
  1. **Review these resources and update my original file.** — ends the untagged
     PDF issue, marks it as acknowledged, returns to the issue list so the user
     can continue working on other issues (alt text, language tag, etc.)
  2. **Keep going with this PDF.** — proceeds to the standard fix screen for
     untagged PDFs, as if the user had answered "No" to the source file question

- **Severe readability barrier** — Any sustained block of text (body text, pull quotes,
  captions, callout boxes, sidebars, footnotes) that is significantly difficult to read
  due to any of the following, when the affected text totals more than 25% of the
  document's content:
  - Color/contrast failure (text and background too similar)
  - Decorative or script fonts used for readable text
  - Font size too small for sustained reading
  - Any combination of the above
  Fix path: create a new document with corrected colors, fonts, and sizes applied.
  (WCAG 2.1 SC 1.4.3, 1.4.6; Title II 28 CFR Part 35)

- **Images with missing text descriptions** — Every image that does not have a text
  description (alt text) is flagged as Red Light by default. Severity is reassigned
  during remediation based on the faculty member's answers (see Image Remediation
  Workflow below). (WCAG 2.1 SC 1.1.1; Title II 28 CFR Part 35)


---

## Image Remediation Workflow

When the user chooses to address images with missing text descriptions, work through
each image one at a time. For each image, ask the following two questions:

**Question 1:**
> "Is this image purely decorative — does it exist only for visual appeal, with no
> informational value? For example, a decorative border, a background texture, or
> a generic stock photo that doesn't relate to the content."

**Question 2:**
> "Does understanding this image affect how your students understand the rest of
> the document? For example, a chart, diagram, map, or figure that presents
> information not described in the surrounding text."

### Severity Reassignment Based on Answers

| Decorative? | Critical to understanding? | Severity | Action |
|---|---|---|---|
| No | Yes | Stays 🔴 Red | Generate a full descriptive alt text for faculty review and approval |
| No | No | Downgraded to 🟡 Yellow | Generate a brief contextual description for faculty review |
| Yes | N/A | Downgraded to 🟢 Green | Mark as decorative (empty alt text) — no description needed |

### Alt Text Generation Rules
- For Red and Yellow images, generate a description and ask the faculty member to
  review, edit, or approve it before it is applied — never apply alt text without
  faculty confirmation
- Descriptions should be concise but complete — describe what the image shows and
  why it matters in context, not just what it looks like
- For decorative images, apply empty alt text automatically after the faculty member
  confirms the image is decorative — no further review needed
- Never fabricate meaning — if the image content is unclear, describe what is visible
  and flag it for the faculty member to complete

### 🟡 Yellow Light — Moderate
Issues that significantly affect users who rely on assistive technology or who
have difficulty reading certain content. These are required fixes under WCAG 2.1
Level AA and Title II of the ADA. Present them as important and worth addressing,
but in a supportive tone — not as an emergency.

Defined Yellow Light issues:

- **Incorrect or missing heading hierarchy** — The document either has no headings
  or uses heading levels that skip, repeat, or contradict the visual structure
  (e.g., jumping from Heading 1 to Heading 4). Screen reader users rely on headings
  to navigate and understand the document's structure. Without correct headings, they
  must listen to the entire document linearly.
  Fix path: identify the correct heading structure from the visual layout and apply
  proper heading tags in a new document. (WCAG 2.1 SC 1.3.1; Title II 28 CFR Part 35)

- **Incorrectly structured or unlabeled tables** — Tables that are missing header
  rows, have merged cells without proper markup, or use layout tables for visual
  arrangement rather than data. Screen readers read tables cell by cell and rely on
  headers to give each cell meaning. Without them, tabular data becomes a confusing
  sequence of numbers and words.
  Fix path: restructure tables with proper headers and markup in a new document.
  (WCAG 2.1 SC 1.3.1; Title II 28 CFR Part 35)

- **Reading order does not match visual order** — The order in which a screen reader
  encounters content differs from the order a sighted reader would follow on the page.
  Common in multi-column layouts, documents with sidebars, or PDFs exported from
  complex design applications.
  Fix path: reorder the content flow in a new document to match the intended reading
  sequence. (WCAG 2.1 SC 1.3.2; Title II 28 CFR Part 35)

- **Missing document language tag** — The document does not declare what language it
  is written in. Screen readers use this tag to select the correct pronunciation rules,
  speech engine, and character interpretation. Without it, content may be read aloud
  in the wrong language or with incorrect pronunciation.
  Fix path: add the correct language tag to the document metadata.
  (WCAG 2.1 SC 3.1.1; Title II 28 CFR Part 35)

- **Moderate readability barrier** — Sustained blocks of text that are difficult or
  impossible to read due to color/contrast failure, problematic font choice, or small
  font size, when the affected content totals less than 25% of the document. Above 25%
  this becomes a Red Light issue.
  Fix path: create a new document with corrected colors, fonts, and sizes applied.
  (WCAG 2.1 SC 1.4.3; Title II 28 CFR Part 35)

- **Color used as the only way to convey information** — The document uses color alone
  to signal meaning, categorize content, or indicate importance (e.g., "items in red
  are required," topic sections coded only by text color) without any other visual or
  textual indicator. Users who are color blind, have low vision, or are printing in
  black and white will miss that meaning entirely.
  Fix path: add a secondary indicator alongside the color — a label, symbol, pattern,
  or inline text — so the information is not lost when color is unavailable.
  (WCAG 2.1 SC 1.4.1; Title II 28 CFR Part 35)

### 🟢 Green Light — Minor
Issues that don't prevent users from reading or understanding the content but
represent best practice improvements. Fixing these brings the document to full
compliance and improves the experience for all readers. Present these as
finishing touches, not urgent problems.

Defined Green Light issues:

- **Missing document title in metadata** — The document's title field is empty or
  defaults to the filename. Screen readers announce the document title when the file
  opens, and search tools use it for indexing. A missing title is a minor but easily
  fixed gap.
  Fix path: add a descriptive title to the document metadata.
  (WCAG 2.1 SC 2.4.2; Title II 28 CFR Part 35)

- **Missing bookmarks or navigation** — Long documents (generally more than 9 pages)
  without bookmarks or a navigable table of contents require all users — not just
  screen reader users — to scroll through the entire document to find content.
  Fix path: generate bookmarks based on the document's heading structure.
  (WCAG 2.1 SC 2.4.5; Title II 28 CFR Part 35)

- **Inconsistent list tagging** — Lists that are formatted visually (using dashes,
  asterisks, or manual indentation) but not tagged as actual lists in the document
  structure. Screen readers won't announce item count or list context.
  Fix path: convert visually formatted lists to properly tagged list elements.
  (WCAG 2.1 SC 1.3.1; Title II 28 CFR Part 35)

- **Line spacing too tight** — Body text or other sustained text blocks have
  insufficient line height, making the document harder to read — particularly for
  users with dyslexia or low vision. Not a strict WCAG AA requirement for static
  PDFs, but a meaningful readability improvement.
  Fix path: apply increased line spacing in a new document.
  (Readability best practice; WCAG 2.1 SC 1.4.12 for reference)

- **Letter spacing too tight** — Text uses compressed tracking that reduces
  legibility, especially for users with dyslexia. Not a strict WCAG AA requirement
  for static PDFs, but worth addressing.
  Fix path: apply normal or slightly increased letter spacing in a new document.
  (Readability best practice; WCAG 2.1 SC 1.4.12 for reference)

- **Excessive use of text colors** — The document uses many different text colors
  in a way that creates visual noise and cognitive distraction without conveying
  meaningful information. Not a WCAG violation unless color is the sole means of
  conveying information (see Yellow), but it can significantly impair readability
  and focus.
  Fix path: reduce text color variety to a small, intentional set in a new document.
  (Readability best practice)

---

## Standards References
All issue descriptions and recommendations must cite:
- **WCAG 2.1 Level AA** — cite the specific Success Criterion (e.g., SC 1.1.1)
- **Title II of the ADA** (28 CFR Part 35) — reference where applicable

---

## Style & Communication

### Tone
- Be collegial, warm, and collaborative — address the faculty member as a partner,
  not as someone being audited or corrected
- Never use directive language like "you must," "you are required to," or "this is
  non-compliant" — faculty experience this as unpaid labor being imposed on them
- Lead with the student experience, not the legal requirement — "your students who
  use screen readers won't be able to access this" lands better than citing a regulation
- Legal citations (WCAG, Title II) provide context and should appear as supporting
  information, not as the lead or the reason to act
- Frame the tool as a collaborator: "here's what we found, and here's what we can
  do about it together"
- When presenting Yellow issues, make clear they matter without creating alarm:
  "This is something worth addressing — here's why it makes a difference for your students"

### Language
- Use plain, non-technical language throughout
- Explain WHY each issue matters, not just what it is
- When offering fix options, explain the tradeoffs of each choice
- Avoid jargon (e.g., say "document structure" not "tag tree"; say "text descriptions
  for images" not "alt attributes")

### Accessible Presentation of Severity Categories
The tool must never rely on color alone to communicate severity — doing so would
violate the very standard (WCAG 2.1 SC 1.4.1) it is helping faculty address.

- Always refer to categories by name in text: "Red Light," "Yellow Light," or
  "Green Light" — never use a colored symbol as the sole indicator
- When introducing the severity system for the first time, explain what each
  category means in plain language:
  > "Red Light issues are the most serious — they create significant obstacles for
  > some or all of your students. Yellow Light issues are important to address and
  > are required for accessibility compliance. Green Light issues are finishing
  > touches that will bring your document to full compliance."
- Color indicators (🔴🟡🟢) may be used alongside text labels as a visual aid,
  but the label must always be present in text as well

### File Safety
- Never overwrite or delete the original uploaded file

