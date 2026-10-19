import { useId, useRef } from "react";
import { Icon } from "./icon.tsx";
import { fieldClass } from "./field.tsx";

/** Props for `SearchBox`. */
export interface SearchBoxProps {
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly placeholder?: string;
  readonly busy?: boolean;
  readonly className?: string;
}

/** A labelled search input with a clear button; `busy` dims the glass while results load. */
export function SearchBox({
  label,
  value,
  onChange,
  placeholder,
  busy = false,
  className = "",
}: SearchBoxProps) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className={`relative ${className}`}>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <Icon
        name="search"
        className={`pointer-events-none absolute top-3 left-3 size-5 text-ink-muted ${busy ? "motion-safe:animate-shimmer" : ""}`}
      />
      <input
        ref={input}
        id={id}
        type="search"
        value={value}
        placeholder={placeholder}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        className={`${fieldClass} px-12 [&::-webkit-search-cancel-button]:appearance-none`}
      />
      {value !== "" && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => {
            onChange("");
            input.current?.focus();
          }}
          className="absolute top-0 right-0 flex size-touch cursor-pointer items-center justify-center text-ink-muted transition-colors hover:text-ink"
        >
          <Icon name="close" />
        </button>
      )}
    </div>
  );
}
