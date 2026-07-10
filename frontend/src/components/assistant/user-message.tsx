import { memo } from "react";
import { motion } from "framer-motion";
import { User } from "lucide-react";

interface UserMessageProps {
  content: string;
}

export const UserMessage = memo(function UserMessage({ content }: UserMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex items-start gap-3 justify-end"
    >
      <div className="max-w-[min(85%,680px)] rounded-2xl rounded-tr-md bg-primary/10 px-4 py-3 shadow-sm ring-1 ring-primary/10">
        <p className="whitespace-pre-wrap text-sm leading-7 text-foreground">{content}</p>
      </div>
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        <User className="h-4 w-4" aria-hidden="true" />
      </div>
    </motion.div>
  );
});
