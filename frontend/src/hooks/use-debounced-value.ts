import { useEffect, useState } from "react";

/** `value`, but only once it has stopped changing for `delayMs`; each change restarts the wait. */
export const useDebouncedValue = <T>(value: T, delayMs: number): T => {
  const [settled, setSettled] = useState(value);
  // A timer lives outside React, so an effect owns it and clears it when the value changes again.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSettled(value);
    }, delayMs);
    return () => {
      clearTimeout(timer);
    };
  }, [value, delayMs]);
  return settled;
};
