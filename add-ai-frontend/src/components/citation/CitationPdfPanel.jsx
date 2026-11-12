/**
 * src/components/citation/CitationPdfPanel.jsx
 *
 * The right-side panel: renders the ORIGINAL PDF for the cited file,
 * scrollable, auto-scrolled to the cited page, with the matched snippet
 * (or OCR bbox) highlighted on that page.
 *
 * ── Alignment fix ──────────────────────────────────────────────────────
 * Highlight rects are computed in the same coordinate space pdf.js used
 * to render the page (`viewport`). Two things previously broke that:
 *
 *   1. The canvas was drawn at `viewport.width x viewport.height` CSS
 *      pixels, then squeezed visually with `max-width:100%; height:auto`.
 *      That made the *visible* canvas a different size than the pixel
 *      grid the highlight boxes were positioned against, so on any panel
 *      narrower than the rendered page, every box landed in the wrong
 *      place (or off the page entirely).
 *   2. On high-DPI screens, drawing at 1x and relying on the browser to
 *      upscale blurred the page and, combined with (1), compounded the
 *      misalignment.
 *
 * Fix: render the canvas at devicePixelRatio using the standard pdf.js
 * "output scale" pattern (canvas.width/height in *device* pixels,
 * canvas.style.width/height in *CSS* pixels), and size the CSS pixels to
 * fit the panel exactly (no `max-width` shrink-to-fit). Highlight rects
 * are computed in that same CSS-pixel `viewport` space, so they now line
 * up 1:1 with what's on screen regardless of screen density or panel
 * width — for both the text-layer match AND the OCR bbox path.
 */
import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import { X, Loader2, FileWarning } from "lucide-react";
import { getAuthHeaders, getDocumentFileUrl } from "../../lib/citationApi";
import { computeHighlightRects, findMatchingItemIndices } from "../../lib/pdfTextHighlight";

// pdf.js needs its worker script. The CDN URL below matches whatever
// pdfjs-dist version npm installs, so it stays in sync automatically and
// needs zero bundler configuration.
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

const PANEL_PADDING_PX = 32; // matches the body's px-4 (16px) * 2

export default function CitationPdfPanel({ citation, onClose }) {
  const [pdfDoc, setPdfDoc] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pageWidth, setPageWidth] = useState(420);

  const scrollContainerRef = useRef(null);
  const pageRefs = useRef({}); // pageNumber -> HTMLDivElement

  const fileId = citation?.file_id;
  const targetPage = Number(citation?.page) || 1;
  const snippet = citation?.snippet || "";

  // Fit the rendered page width to the actual panel width so pages are
  // never CSS-scaled after the fact (see alignment note above).
  useLayoutEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const measure = () => setPageWidth(Math.max(280, el.clientWidth - PANEL_PADDING_PX));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Load the document whenever the citation's file changes.
  useEffect(() => {
    if (!fileId) return;
    let cancelled = false;

    setLoading(true);
    setError(null);
    setPdfDoc(null);
    pageRefs.current = {};

    const loadingTask = pdfjsLib.getDocument({
      url: getDocumentFileUrl(fileId),
      httpHeaders: getAuthHeaders(),
    });

    loadingTask.promise
      .then((doc) => {
        if (cancelled) return;
        setPdfDoc(doc);
        setNumPages(doc.numPages);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to load citation PDF:", err);
        setError("Could not load this document. It may have been removed.");
        setLoading(false);
      });

    return () => {
      cancelled = true;
      loadingTask.destroy?.();
    };
  }, [fileId]);

  // Once loaded, scroll to the target page.
  useEffect(() => {
    if (!pdfDoc) return;
    const el = pageRefs.current[targetPage];
    if (el && scrollContainerRef.current) {
      const t = setTimeout(() => {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 150);
      return () => clearTimeout(t);
    }
  }, [pdfDoc, targetPage]);

  if (!citation) return null;

  return (
    <div className="fixed right-0 top-0 z-[1000] flex h-screen w-[min(520px,92vw)] flex-col border-l border-border bg-background shadow-2xl">
      <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-foreground" title={citation.source}>
            {citation.source || "Document"}
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            Page {targetPage}
            {citation.bbox ? " · scanned page (OCR match)" : snippet ? " · text match" : ""}
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Close citation viewer"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div ref={scrollContainerRef} className="scrollbar-thin flex-1 overflow-y-auto bg-muted/40 px-4 py-4">
        {loading && (
          <div className="mt-10 flex flex-col items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading document…
          </div>
        )}
        {error && (
          <div className="mt-10 flex flex-col items-center gap-2 text-sm text-destructive">
            <FileWarning className="h-4 w-4" />
            {error}
          </div>
        )}

        {pdfDoc &&
          Array.from({ length: numPages }, (_, i) => i + 1).map((pageNumber) => (
            <PdfPage
              key={pageNumber}
              pdfDoc={pdfDoc}
              pageNumber={pageNumber}
              targetWidth={pageWidth}
              isTarget={pageNumber === targetPage}
              snippet={pageNumber === targetPage ? snippet : ""}
              bbox={pageNumber === targetPage ? citation.bbox : null}
              pageWidthPt={citation.page_width}
              pageHeightPt={citation.page_height}
              registerRef={(el) => (pageRefs.current[pageNumber] = el)}
            />
          ))}
      </div>
    </div>
  );
}

/**
 * One page: renders its canvas at the exact CSS pixel size the highlight
 * rects are computed in (see module docblock), and — only on the target
 * page — overlays a highlight for the matched snippet. Uses citation.bbox
 * directly when present (OCR'd pages); otherwise falls back to searching
 * pdf.js's text layer for `snippet` (normal, non-scanned pages).
 */
function PdfPage({ pdfDoc, pageNumber, targetWidth, isTarget, snippet, bbox, pageWidthPt, pageHeightPt, registerRef }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [highlightRects, setHighlightRects] = useState([]);
  const [rendered, setRendered] = useState(false);
  const [cssSize, setCssSize] = useState({ width: targetWidth, height: targetWidth * 1.3 });

  useEffect(() => {
    let cancelled = false;

    pdfDoc.getPage(pageNumber).then(async (page) => {
      if (cancelled) return;

      // Scale so the page's CSS width matches the panel exactly — no
      // post-hoc CSS shrink, so highlight coordinates stay valid.
      const unscaledViewport = page.getViewport({ scale: 1 });
      const fitScale = targetWidth / unscaledViewport.width;
      const viewport = page.getViewport({ scale: fitScale });

      const canvas = canvasRef.current;
      if (!canvas) return;
      const context = canvas.getContext("2d");

      // Render at devicePixelRatio for crisp text on high-DPI screens,
      // while keeping the CSS box (and therefore highlight coordinates)
      // in plain `viewport` units.
      const outputScale = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;
      setCssSize({ width: viewport.width, height: viewport.height });

      const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined;

      await page.render({ canvasContext: context, viewport, transform }).promise;
      if (cancelled) return;
      setRendered(true);

      if (!isTarget) return;

      // OCR'd/scanned pages: use the exact bbox the backend computed
      // from OCR word coordinates, converting PDF point space straight
      // into this page's CSS-pixel viewport space (flipping Y, since
      // PDF's origin is bottom-left but canvas/DOM is top-left).
      if (bbox && pageWidthPt && pageHeightPt) {
        const scaleX = viewport.width / pageWidthPt;
        const scaleY = viewport.height / pageHeightPt;
        setHighlightRects([
          {
            left: bbox.x0 * scaleX,
            top: (pageHeightPt - bbox.y1) * scaleY,
            width: (bbox.x1 - bbox.x0) * scaleX,
            height: (bbox.y1 - bbox.y0) * scaleY,
          },
        ]);
        return;
      }

      // Normal pages: search the embedded text layer for the snippet.
      if (snippet) {
        const textContent = await page.getTextContent();
        if (cancelled) return;
        const matchedIndices = findMatchingItemIndices(textContent, snippet);
        if (matchedIndices.length > 0) {
          setHighlightRects(computeHighlightRects(textContent, matchedIndices, viewport));
        }
      }
    });

    return () => {
      cancelled = true;
    };
  }, [pdfDoc, pageNumber, targetWidth, isTarget, snippet, bbox, pageWidthPt, pageHeightPt]);

  return (
    <div
      ref={(el) => {
        containerRef.current = el;
        registerRef(el);
      }}
      className={
        "mb-4 flex flex-col items-center" +
        (isTarget ? " rounded-md p-1 ring-2 ring-primary ring-offset-2 ring-offset-muted" : "")
      }
    >
      <div className="mb-1 text-[11px] text-muted-foreground">Page {pageNumber}</div>
      <div className="relative inline-block" style={{ width: cssSize.width, height: cssSize.height }}>
        <canvas ref={canvasRef} className="rounded-sm bg-white shadow-sm" />
        {rendered &&
          highlightRects.map((rect, i) => (
            <div
              key={i}
              className="pointer-events-none absolute rounded-[2px]"
              style={{
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
                backgroundColor: "rgba(250, 204, 21, 0.55)",
                boxShadow: "0 0 0 1px rgba(202, 138, 4, 0.5)",
              }}
            />
          ))}
      </div>
    </div>
  );
}
