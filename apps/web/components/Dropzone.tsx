"use client";

import { useDropzone } from "react-dropzone";
import { UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";

type Props = {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
};

export function Dropzone({ onFiles, disabled }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
    disabled,
    onDrop: (accepted, rejected) => {
      if (rejected.length > 0) {
        toast.error("Only PDFs are accepted.");
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
          {isDragActive ? "Drop your PDFs here" : "Drop PDFs here, or click to browse"}
        </p>
        <p className="text-xs text-muted-foreground">PDFs only. Multiple files supported.</p>
      </div>
    </div>
  );
}
