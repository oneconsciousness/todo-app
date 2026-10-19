import { Icon } from "./icon.tsx";

/** Props for `Checkbox`. */
export interface CheckboxProps {
  readonly label: string;
  readonly checked: boolean;
  readonly onChange: (checked: boolean) => void;
}

/** A native checkbox drawn as a ledger tick box, with a 44px hit area around a 20px box. */
export function Checkbox({ label, checked, onChange }: CheckboxProps) {
  return (
    <span className="relative inline-flex size-touch shrink-0 items-center justify-center">
      <input
        type="checkbox"
        aria-label={label}
        checked={checked}
        onChange={(event) => {
          onChange(event.target.checked);
        }}
        className="peer absolute inset-0 m-0 cursor-pointer appearance-none outline-none"
      />
      <span
        aria-hidden="true"
        className="pointer-events-none flex size-5 items-center justify-center rounded-control border border-rule-strong bg-sheet text-on-primary transition-colors peer-checked:border-primary peer-checked:bg-primary peer-hover:border-ink peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus [&>svg]:opacity-0 peer-checked:[&>svg]:opacity-100"
      >
        <Icon name="check" className="size-4" />
      </span>
    </span>
  );
}
