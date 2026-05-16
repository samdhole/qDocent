"use client";

import { useDropzone } from "react-dropzone";
import { UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";

type Props = {
  onFiles: (files: Array<File>) => void;
  disabled?: boolean;
  accept?: Record<string, Array<string>>;
};

const PDF_ONLY: Record<string, Array<string>> = { "application/pdf": [".pdf"] };

export function Dropzone({ onFiles, disabled, accept = PDF_ONLY }: Props) {
  const extensions = Object.values(accept).flat().join(", ");

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept,
    multiple: true,
    disabled,
    onDrop: (accepted, rejected) => {
      if (rejected.length > 0) {
        toast.error(`Only ${extensions} files are accepted.`);
      }
      if (accepted.length > 0) {
        onFiles(accepted);
      }
    },
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "border-2 border-dashed rounded-md p-8 text-center cursor-pointer transition-colors",
        "bg-muted/40 hover:bg-muted/60",
        isDragActive && "border-primary bg-primary/5",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2">
        <UploadCloud className="size-8 text-muted-foreground" />
        <p className="text-sm font-medium">
          {isDragActive ? `Drop your files here` : `Drop files here, or click to browse`}
        </p>
        <p className="text-xs text-muted-foreground">
          {accept === PDF_ONLY /* Identity check: PDF_ONLY is a const, so === is correct */
            ? "PDFs only on this page. Open a Notebook to upload DOCX, PPTX, or URLs."
            : `Accepted: ${extensions}`}
        </p>
      </div>
    </div>
  );
}
