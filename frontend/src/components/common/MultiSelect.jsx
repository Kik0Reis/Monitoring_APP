import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown } from "lucide-react";

import "./multi-select.css";

// dropdown list where more than one option can be ticked, value is the array of selected options
// the list is drawn in a portal with fixed position so the scrolling table does not cut it
function MultiSelect({ options, value, onChange, ariaLabel, allLabel = "All" }) {
  const selected = value ?? [];

  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const buttonRef = useRef(null);
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    // closes the list on a click outside, escape, resize or a scroll outside it
    function handleEvent(event) {
      const inside =
        panelRef.current?.contains(event.target) || buttonRef.current?.contains(event.target);

      if (event.type === "keydown" && event.key !== "Escape") return;
      if ((event.type === "mousedown" || event.type === "scroll") && inside) return;

      setOpen(false);
    }

    document.addEventListener("mousedown", handleEvent);
    document.addEventListener("keydown", handleEvent);
    window.addEventListener("resize", handleEvent);
    window.addEventListener("scroll", handleEvent, true);

    return () => {
      document.removeEventListener("mousedown", handleEvent);
      document.removeEventListener("keydown", handleEvent);
      window.removeEventListener("resize", handleEvent);
      window.removeEventListener("scroll", handleEvent, true);
    };
  }, [open]);

  // opens the list under the button, or closes it when it is open
  function toggleOpen() {
    if (open) {
      setOpen(false);
      return;
    }

    const rect = buttonRef.current.getBoundingClientRect();
    setPosition({ top: rect.bottom + 4, left: rect.left, minWidth: Math.max(rect.width, 180) });
    setOpen(true);
  }

  // ticks or unticks one option
  function toggleOption(option) {
    onChange(
      selected.includes(option)
        ? selected.filter((item) => item !== option)
        : [...selected, option]
    );
  }

  const buttonLabel =
    selected.length === 0
      ? allLabel
      : selected.length <= 2
        ? selected.join(", ")
        : `${selected.length} selected`;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className={`multi-select-button ${selected.length > 0 ? "has-value" : ""}`}
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={toggleOpen}
      >
        <span className="multi-select-button-text">{buttonLabel}</span>
        <ChevronDown size={14} />
      </button>

      {open &&
        position &&
        createPortal(
          <div
            ref={panelRef}
            className="multi-select-panel"
            style={position}
            role="listbox"
            aria-multiselectable="true"
            aria-label={ariaLabel}
          >
            {options.length === 0 ? (
              <div className="multi-select-empty">No options</div>
            ) : (
              <div className="multi-select-options">
                {options.map((option) => (
                  <label key={option} className="multi-select-option" role="option" aria-selected={selected.includes(option)}>
                    <input
                      type="checkbox"
                      checked={selected.includes(option)}
                      onChange={() => toggleOption(option)}
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
            )}

            {selected.length > 0 && (
              <button type="button" className="multi-select-clear" onClick={() => onChange([])}>
                Clear selection
              </button>
            )}
          </div>,
          document.body
        )}
    </>
  );
}

export default MultiSelect;
