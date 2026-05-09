"use client";
import { pdfjs } from "react-pdf";

// Match the pdfjs-dist version installed in package.json
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;
