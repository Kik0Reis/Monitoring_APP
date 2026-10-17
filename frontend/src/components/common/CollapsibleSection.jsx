import { useState } from "react";
import { ChevronDown } from "lucide-react";

// a detail section whose body opens and closes when the header is clicked
// it controls itself, or the parent can control it with open and onToggle
function CollapsibleSection({
  title,
  count,
  badge,
  defaultOpen = false,
  open: controlledOpen,
  onToggle,
  actions,
  children,
}) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : internalOpen;

  // opens or closes the section
  function toggle() {
    if (isControlled) {
      onToggle?.(!isOpen);
    } else {
      setInternalOpen((value) => !value);
    }
  }

  return (
    <section className={`detail-section collapsible-section ${isOpen ? "open" : ""}`}>
      <button type="button" className="collapsible-section-header" onClick={toggle} aria-expanded={isOpen}>
        <span className="collapsible-section-title">
          <ChevronDown size={16} className="collapsible-chevron" />
          <h3>{title}</h3>
          {typeof count === "number" && <span className="collapsible-count">{count}</span>}
          {badge}
        </span>

        {actions && (
          <span className="collapsible-section-actions" onClick={(event) => event.stopPropagation()}>
            {actions}
          </span>
        )}
      </button>

      {isOpen && <div className="collapsible-section-body">{children}</div>}
    </section>
  );
}

export default CollapsibleSection;
