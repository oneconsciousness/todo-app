import { type ComponentProps, type MouseEvent, type ReactNode, createContext, use } from "react";

type Navigate = (href: string) => void;

const NavigationContext = createContext<Navigate | null>(null);

/** Props for `NavigationProvider`. */
export interface NavigationProviderProps {
  readonly navigate: Navigate;
  readonly children: ReactNode;
}

/** Lets every `Link` below it navigate inside the app instead of reloading the page. */
export function NavigationProvider({ navigate, children }: NavigationProviderProps) {
  return <NavigationContext value={navigate}>{children}</NavigationContext>;
}

/** True for a click the app should handle itself: the main button, with no modifier key. */
export const isPlainClick = (event: MouseEvent): boolean =>
  event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;

/** Props for `Link`: a native anchor that always has an `href`. */
export interface LinkProps extends ComponentProps<"a"> {
  readonly href: string;
}

/** A real link: a plain click navigates in the app, any other click is left to the browser. */
export function Link({ href, onClick, ...props }: LinkProps) {
  const navigate = use(NavigationContext);
  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event);
    if (!navigate || event.defaultPrevented || !isPlainClick(event)) return;
    event.preventDefault();
    navigate(href);
  };
  return <a href={href} onClick={handleClick} {...props} />;
}
