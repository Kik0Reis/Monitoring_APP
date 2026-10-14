import { useEffect, useRef } from "react";
import flatpickr from "flatpickr";
import { Portuguese } from "flatpickr/dist/esm/l10n/pt.js";

import "flatpickr/dist/flatpickr.min.css";
import "flatpickr/dist/themes/dark.css";


function PickerInput({ mode, value, onChange, className, ariaLabel }) {
  const inputRef = useRef(null);
  const pickerRef = useRef(null);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    valueRef.current = value;
    onChangeRef.current = onChange;
  });

  useEffect(() => {
    const isDate = mode === "date";

    const picker = flatpickr(inputRef.current, {
      locale: Portuguese,
      allowInput: true,
      defaultDate: valueRef.current || undefined,
      altInputClass: className,
      ...(isDate
        ? { dateFormat: "Y-m-d", altInput: true, altFormat: "d/m/Y" }
        : { enableTime: true, noCalendar: true, dateFormat: "H:i", time_24hr: true }),
      onChange: (_dates, dateString) => onChangeRef.current(dateString),
    });

    // with altInput the visible field is flatpickr's copy, not our <input>
    const visible = picker.altInput ?? picker.input;
    visible.setAttribute("aria-label", ariaLabel);
    visible.setAttribute("autocomplete", "off");

    pickerRef.current = picker;
    return () => picker.destroy();
  }, [mode, className, ariaLabel]);

  // follow changes made from outside (e.g. "Clear filters")
  useEffect(() => {
    const picker = pickerRef.current;
    if (picker && picker.input.value !== (value || "")) {
      picker.setDate(value || null, false);
    }
  }, [value]);

  // Date mode: flatpickr shows its own formatted copy of the field (dd/mm/aaaa)
  // and keeps this one only to hold the yyyy-mm-dd value, so it must be
  // hidden. Time mode has no copy: this is the visible field.
  return (
    <input
      ref={inputRef}
      type={mode === "date" ? "hidden" : "text"}
      className={className}
      placeholder={mode === "date" ? "dd/mm/aaaa" : "hh:mm"}
    />
  );
}

export default PickerInput;
