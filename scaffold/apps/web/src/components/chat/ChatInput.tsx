import { PaperPlaneRight } from '@phosphor-icons/react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';

interface ChatInputProps {
  disabled?: boolean;
  onSend: (text: string) => void;
}

export function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-surface)] p-2"
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        rows={1}
        placeholder="向课程助教提问…(Enter 换行,点击按钮发送)"
        className="max-h-32 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-[var(--color-fg-muted)]"
      />
      <Button type="submit" size="icon" disabled={disabled || !value.trim()} aria-label="发送">
        <PaperPlaneRight size={16} weight="fill" />
      </Button>
    </form>
  );
}
