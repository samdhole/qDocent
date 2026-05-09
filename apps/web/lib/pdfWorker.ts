"use client";
import { pdfjs } from "react-pdf";

// CDN worker — requires network access. For offline or CSP-restricted deployments,
// copy node_modules/pdfjs-dist/build/pdf.worker.min.mjs to public/pdf.worker.min.mjs
// and change workerSrc to "/pdf.worker.min.mjs".

// Match the pdfjs-dist version installed in package.json
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;
