# Speculara MVP demo package

Open **Speculara_MVP_10_Slides.pdf** for a ten-slide presentation. Slide 10 is the demo. **Speculara_MVP_10_Slides.html** is a standalone browser version with keyboard navigation, speaker notes and source links. It needs no server or external assets.

- Arrow keys / Page Up / Page Down: change slides
- `N`: speaker notes
- `S`: full source list
- `F`: browser fullscreen

**Speculara_Presenter_Script_and_Reviewer.pdf** includes the speaking script, tech-stack explanations, important function map and likely panel questions. The editable text version is **Speculara_Script_and_Reviewer.md**.

**Speculara_Documentation.pdf** is the complete user and technical guide, including methods, architecture, palette, neumorphism, proposed brand-name/logo interpretation, maintenance log, limitations and source references. Its editable text is **Speculara_Documentation.md**. **Speculara_Feature_Code.md** contains exact short code excerpts with file and line locators.

**Speculara_Logo.svg** and **Speculara_Logo.png** preserve the supplied artwork. The site header uses the SVG, the favicon uses a resized PNG and the browser title is **Speculara | Social Media Analysis**.

## Demo

1. Keep the backend at localhost:8000 and frontend at localhost:8443 running.
2. In the app choose **Analyze CSV / Excel data**.
3. Select either sample under `../speculara-samples-20261112/` (or `samples/` in the ZIP). These are the same 40 fictional posts.
4. Explore all six views and explicitly identify the data as synthetic.
5. Ask the assistant a demand question, generate strategy and inspect engine/notice labels. Source buttons appear only for actual supplied URLs; synthetic rows deliberately have none.

See **MVP-QA.md** and the JSON verification logs for the final test results and service limits. CSV/Excel and numerical views are the repeatable route; external connectors and Gemma availability can vary. This package contains PDF and standalone HTML presentation formats.
