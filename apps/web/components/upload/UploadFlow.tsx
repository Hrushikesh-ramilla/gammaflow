"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, FileText, BookOpen, Upload, X, Check, AlertCircle, Loader2 } from "lucide-react";

type DocumentRole = "SYLLABUS" | "TEXTBOOK" | "NOTES";

interface UploadedFile {
  role: DocumentRole;
  file: File;
  status: "pending" | "uploading" | "processing" | "done" | "error";
  progress: number;
  ocrWarnings?: number[];
  error?: string;
}

const ROLES: { role: DocumentRole; icon: typeof FileText; label: string; desc: string; color: string }[] = [
  {
    role: "SYLLABUS",
    icon: Brain,
    label: "Syllabus",
    desc: "Your professor's topic list or course outline",
    color: "from-indigo-500 to-violet-500",
  },
  {
    role: "TEXTBOOK",
    icon: BookOpen,
    label: "Textbook",
    desc: "Reference book PDF (text or scanned)",
    color: "from-violet-500 to-purple-500",
  },
  {
    role: "NOTES",
    icon: FileText,
    label: "Professor Notes",
    desc: "Handwritten notes, slides, WhatsApp PDFs",
    color: "from-purple-500 to-pink-500",
  },
];

export function UploadFlow({ syllabusId, onComplete }: { syllabusId: string; onComplete: () => void }) {
  const [uploads, setUploads] = useState<Record<DocumentRole, UploadedFile | null>>({
    SYLLABUS: null,
    TEXTBOOK: null,
    NOTES: null,
  });
  const [step, setStep] = useState<"upload" | "processing" | "done">("upload");

  const handleFileDrop = useCallback(
    (role: DocumentRole, event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const file = event.dataTransfer.files[0];
      if (file && file.type === "application/pdf") {
        setUploads((prev) => ({
          ...prev,
          [role]: { role, file, status: "pending", progress: 0 },
        }));
      }
    },
    []
  );

  const handleFileSelect = useCallback((role: DocumentRole, event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploads((prev) => ({
        ...prev,
        [role]: { role, file, status: "pending", progress: 0 },
      }));
    }
  }, []);

  const removeFile = useCallback((role: DocumentRole) => {
    setUploads((prev) => ({ ...prev, [role]: null }));
  }, []);

  const canProcess = uploads.SYLLABUS !== null;

  const startProcessing = async () => {
    setStep("processing");
    // TODO: wire to actual upload API
    setTimeout(() => setStep("done"), 3000);
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-10">
        <h2 className="text-2xl font-bold text-white mb-2">Upload your materials</h2>
        <p className="text-gray-400">
          Syllabus is required. Textbook and notes make answers much richer.
        </p>
      </div>

      <div className="space-y-4 mb-8">
        {ROLES.map(({ role, icon: Icon, label, desc, color }) => {
          const upload = uploads[role];
          const isRequired = role === "SYLLABUS";

          return (
            <motion.div
              key={role}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass rounded-2xl p-4"
            >
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center flex-shrink-0`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-white">{label}</h3>
                    {isRequired && (
                      <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full">
                        required
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400">{desc}</p>

                  {/* File drop zone or uploaded file */}
                  {upload ? (
                    <div className="mt-3 flex items-center gap-3 bg-white/5 rounded-xl px-4 py-2">
                      <FileText className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span className="text-sm text-gray-300 truncate flex-1">{upload.file.name}</span>
                      {upload.status === "done" && <Check className="w-4 h-4 text-emerald-400" />}
                      {upload.status === "error" && <AlertCircle className="w-4 h-4 text-red-400" />}
                      {upload.status === "processing" && (
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                          <span className="text-xs text-indigo-300">{upload.progress}%</span>
                        </div>
                      )}
                      {upload.status === "pending" && (
                        <button
                          onClick={() => removeFile(role)}
                          className="text-gray-500 hover:text-red-400 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ) : (
                    <div
                      className="mt-3 border-2 border-dashed border-gray-700 hover:border-indigo-500 rounded-xl p-4 text-center cursor-pointer transition-colors group"
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => handleFileDrop(role, e)}
                    >
                      <input
                        type="file"
                        accept="application/pdf"
                        className="hidden"
                        id={`file-${role}`}
                        onChange={(e) => handleFileSelect(role, e)}
                      />
                      <label htmlFor={`file-${role}`} className="cursor-pointer">
                        <Upload className="w-5 h-5 text-gray-500 group-hover:text-indigo-400 mx-auto mb-1 transition-colors" />
                        <p className="text-sm text-gray-500 group-hover:text-gray-300 transition-colors">
                          Drop PDF here or <span className="text-indigo-400">browse</span>
                        </p>
                        <p className="text-xs text-gray-600 mt-1">Supports text PDFs, scanned, handwritten notes</p>
                      </label>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Process button */}
      <div className="flex justify-end">
        <motion.button
          onClick={startProcessing}
          disabled={!canProcess || step === "processing"}
          whileHover={{ scale: canProcess ? 1.02 : 1 }}
          whileTap={{ scale: canProcess ? 0.98 : 1 }}
          className={`
            flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-base transition-all
            ${canProcess
              ? "bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
              : "bg-gray-800 text-gray-500 cursor-not-allowed"
            }
          `}
        >
          {step === "processing" ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Building knowledge graph…
            </>
          ) : (
            <>
              <Brain className="w-5 h-5" />
              Build my knowledge graph
            </>
          )}
        </motion.button>
      </div>
    </div>
  );
}
