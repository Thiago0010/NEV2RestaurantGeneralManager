import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef(({ className, type, showPassword, togglePassword, ...props }, ref) => {
  const inputRef = React.useRef(ref);
  React.useImperativeHandle(ref, () => inputRef.current, []);
  
  // Handle password visibility toggle without remounting
  const handleTogglePassword = React.useCallback(() => {
    if (inputRef.current && showPassword !== undefined) {
      inputRef.current.type = inputRef.current.type === 'password' ? 'text' : 'password';
    }
    if (togglePassword) togglePassword();
  }, [showPassword, togglePassword]);

  return (
    <div className="relative">
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          className
        )}
        ref={inputRef}
        {...props}
      />
      {showPassword !== undefined && togglePassword && (
        <button
          type="button"
          onClick={handleTogglePassword}
          tabIndex={-1}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors focus-visible-ring rounded p-1"
          aria-label={props.type === 'password' ? "Mostrar senha" : "Ocultar senha"}
          aria-pressed={props.type === 'text'}
        >
          {props.type === 'password' ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" /></svg>
          )}
        </button>
      )}
    </div>
  );
})
Input.displayName = "Input"

export { Input }
